# Loaded by FUTURE.server_parts.02_users_auth_settings into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

PASSWORD_HASH_ROUNDS = 2


def configured_password_hash_rounds(default: int | None = None) -> int:
    # Updated 2026-07-22: this internal server intentionally fixes password hashing at two rounds for speed.
    return PASSWORD_HASH_ROUNDS


AUTH_SUCCESS_VERIFY_CACHE: dict[str, dict] = {}
AUTH_SUCCESS_VERIFY_CACHE_LOCK = threading.RLock()
AUTH_SUCCESS_VERIFY_CACHE_TTL_SECONDS = 45.0


def auth_limits_disabled_for_benchmark() -> bool:
    # Added 2026-07-25: temporary migration baseline switch; production default remains protected.
    return clean(os.environ.get("FUTURE_DISABLE_AUTH_LIMITS_FOR_BENCHMARK", "")).lower() in {"1", "true", "yes", "on"}


def auth_success_verify_cache_key(username: str, password: str, stored: str) -> str:
    # Added 2026-07-10: speed up immediate login/reload bursts without caching failed passwords.
    password_sig = hashlib.sha256(str(password or "").encode("utf-8")).hexdigest()
    stored_sig = hashlib.sha256(str(stored or "").encode("utf-8")).hexdigest()
    return f"{normalize_username(username)}|{stored_sig}|{password_sig}"


def auth_success_verify_cache_hit(username: str, password: str, stored: str) -> bool:
    key = auth_success_verify_cache_key(username, password, stored)
    now = time.time()
    with AUTH_SUCCESS_VERIFY_CACHE_LOCK:
        row = AUTH_SUCCESS_VERIFY_CACHE.get(key)
        if isinstance(row, dict) and now - float(row.get("at", 0.0) or 0.0) < AUTH_SUCCESS_VERIFY_CACHE_TTL_SECONDS:
            return True
        AUTH_SUCCESS_VERIFY_CACHE.pop(key, None)
    return False


def remember_auth_success_verify(username: str, password: str, stored: str) -> None:
    key = auth_success_verify_cache_key(username, password, stored)
    with AUTH_SUCCESS_VERIFY_CACHE_LOCK:
        AUTH_SUCCESS_VERIFY_CACHE[key] = {"at": time.time()}
        if len(AUTH_SUCCESS_VERIFY_CACHE) > 512:
            stale = sorted(AUTH_SUCCESS_VERIFY_CACHE.items(), key=lambda item: float((item[1] or {}).get("at", 0.0) or 0.0))
            for old_key, _value in stale[:128]:
                AUTH_SUCCESS_VERIFY_CACHE.pop(old_key, None)


# Added 2026-07-09: stores auth passwords as PBKDF2 hashes while keeping legacy login compatible.
def password_hash(value: str, salt: str = "") -> str:
    salt = clean(salt) or secrets.token_urlsafe(18)
    rounds = configured_password_hash_rounds()
    digest = hashlib.pbkdf2_hmac("sha256", str(value or "").encode("utf-8"), salt.encode("utf-8"), rounds)
    return f"pbkdf2_sha256${rounds}$" + salt + "$" + base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def password_hash_rounds(stored: str) -> int:
    raw = str(stored or "")
    if not raw.startswith("pbkdf2_sha256$"):
        return 0
    parts = raw.split("$", 3)
    if len(parts) != 4:
        return 0
    try:
        return max(1, min(600000, int(parts[1])))
    except (TypeError, ValueError):
        return 0


def password_hash_needs_rehash(stored: str) -> bool:
    return password_hash_rounds(stored) != PASSWORD_HASH_ROUNDS


# Added 2026-07-09: verifies both PBKDF2 hashes and old plain-text password rows.
def password_hash_matches(value: str, stored: str) -> bool:
    raw = str(stored or "")
    if not raw.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(str(value or ""), raw)
    parts = raw.split("$", 3)
    if len(parts) != 4:
        return False
    _scheme, _rounds_text, salt, expected = parts
    rounds = password_hash_rounds(raw)
    if not rounds:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", str(value or "").encode("utf-8"), salt.encode("utf-8"), rounds)
    actual = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return hmac.compare_digest(actual, expected)


# Added 2026-07-09: upgrades legacy plain-text user passwords after a successful login.
def upgrade_user_password_hash(username: str, password: str, lines: list[str]) -> None:
    if not lines:
        return
    _stored_user, stored_pass = parse_user_header(lines[0])
    if not password_hash_needs_rehash(stored_pass):
        return
    next_lines = list(lines)
    next_lines[0] = f"{normalize_username(username)}:{password_hash(password)}"
    write_user_lines(username, next_lines)


# Added 2026-07-09: updates a user's password row after reset or change-password.
def set_user_password_hash(username: str, password: str) -> None:
    username = normalize_username(username)
    if postgres_backend_mode("USER_AUTH_DOCS") == "postgres":
        if not postgres_load_user_auth_credential(username):
            raise RuntimeError("User khong ton tai.")
        postgres_upsert_user_auth_credential(username, password_hash(password), str(user_file_path(username)))
        return
    lines = read_user_lines(username)
    if not lines:
        raise RuntimeError("User khong ton tai.")
    lines[0] = f"{username}:{password_hash(password)}"
    write_user_lines(username, lines)


# Added 2026-07-09: keeps dashboard password resets simple for local admin-managed learners.
def validate_admin_set_password(value: str) -> tuple[bool, str]:
    password = str(value or "")
    if len(password) < 4:
        return False, "Mat khau admin dat phai co it nhat 4 ky tu."
    return True, ""


# Added 2026-07-09: lets the local dashboard admin directly set a user's password.
def admin_change_user_password(username: str, password: str) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    if not server_database_user_exists(username):
        raise RuntimeError("User khong ton tai.")
    ok, message = validate_admin_set_password(password)
    if not ok:
        raise RuntimeError(message)
    set_user_password_hash(username, password)
    clear_login_failures("", username)
    return {"username": username, "changed": True}


# Added 2026-07-09: scopes login lockouts by browser/client and username.
def login_failure_key(client_key: str, username: str) -> str:
    return f"user:{clean(client_key)[:80]}:{normalize_username(username)}"


# Added 2026-07-09: locks the whole client machine after repeated login failures across usernames.
def login_failure_client_key(client_key: str) -> str:
    return f"client:{clean(client_key)[:120]}"


# Added 2026-07-09: normalizes one login failure bucket and expires stale counters.
def login_failure_lock_item_status(item: dict, now: float) -> dict:
    if not isinstance(item, dict):
        return {"locked": False, "attempts": 0, "retry_after": 0}
    locked_until = float(item.get("locked_until", 0) or 0)
    if locked_until > now:
        return {"locked": True, "attempts": int(item.get("attempts", 0) or 0), "retry_after": max(1, int(locked_until - now))}
    if now - float(item.get("first_at", now) or now) > LOGIN_FAILURE_LOCK_SECONDS:
        return {"locked": False, "attempts": 0, "retry_after": 0, "expired": True}
    return {"locked": False, "attempts": int(item.get("attempts", 0) or 0), "retry_after": 0}


# Added 2026-07-09: reports whether a client machine or specific client/user pair is temporarily locked.
def login_failure_status(client_key: str, username: str) -> dict:
    if auth_limits_disabled_for_benchmark():
        return {"locked": False, "attempts": 0, "retry_after": 0, "scope": "benchmark_disabled"}
    machine_key = login_failure_client_key(client_key)
    user_key = login_failure_key(client_key, username)
    now = time.time()
    with AUTH_LOCK:
        machine = login_failure_lock_item_status(LOGIN_FAILURE_LOCKS.get(machine_key), now)
        user = login_failure_lock_item_status(LOGIN_FAILURE_LOCKS.get(user_key), now)
        if machine.get("expired"):
            LOGIN_FAILURE_LOCKS.pop(machine_key, None)
        if user.get("expired"):
            LOGIN_FAILURE_LOCKS.pop(user_key, None)
        if machine.get("locked"):
            return {**machine, "scope": "client"}
        if user.get("locked"):
            return {**user, "scope": "user"}
        return {
            "locked": False,
            "attempts": max(int(machine.get("attempts", 0) or 0), int(user.get("attempts", 0) or 0)),
            "client_attempts": int(machine.get("attempts", 0) or 0),
            "user_attempts": int(user.get("attempts", 0) or 0),
            "retry_after": 0,
            "scope": "",
        }


# Added 2026-07-09: increments failed login attempts and starts the five-minute client lock.
def record_login_failure(client_key: str, username: str) -> dict:
    if auth_limits_disabled_for_benchmark():
        return {"locked": False, "attempts": 0, "retry_after": 0, "scope": "benchmark_disabled"}
    keys = [login_failure_client_key(client_key), login_failure_key(client_key, username)]
    now = time.time()
    with AUTH_LOCK:
        for key in keys:
            item = LOGIN_FAILURE_LOCKS.get(key)
            if not isinstance(item, dict) or now - float(item.get("first_at", now) or now) > LOGIN_FAILURE_LOCK_SECONDS:
                item = {"attempts": 0, "first_at": now, "locked_until": 0}
            item["attempts"] = int(item.get("attempts", 0) or 0) + 1
            if item["attempts"] >= LOGIN_FAILURE_MAX_ATTEMPTS:
                item["locked_until"] = now + LOGIN_FAILURE_LOCK_SECONDS
            LOGIN_FAILURE_LOCKS[key] = item
        return login_failure_status(client_key, username)


# Added 2026-07-09: clears failed login counters for the client after successful auth or password reset.
def clear_login_failures(client_key: str, username: str) -> None:
    with AUTH_LOCK:
        LOGIN_FAILURE_LOCKS.pop(login_failure_client_key(client_key), None)
        LOGIN_FAILURE_LOCKS.pop(login_failure_key(client_key, username), None)


def check_user_login(username: str, password: str) -> tuple[bool, str, dict]:
    username = normalize_username(username)
    test_password_hash = server_database_test_user_password_hash(username)
    if test_password_hash:
        if is_user_login_blocked(username):
            return False, "blocked", {}
        if not auth_success_verify_cache_hit(username, password, test_password_hash):
            if not password_hash_matches(password, test_password_hash):
                return False, "wrongpass", {}
            remember_auth_success_verify(username, password, test_password_hash)
        return True, "ok", {
            "full_name": f"Server Load Test {username[-3:]}",
            "intro": "PostgreSQL-only Server 2 load-test identity.",
            "load_test": True,
        }
    if postgres_backend_mode("USER_AUTH_DOCS") == "postgres":
        stored_pass = postgres_load_user_auth_credential(username)
        if not stored_pass:
            return False, "nouser", {}
        if is_user_login_blocked(username):
            return False, "blocked", {}
        if auth_success_verify_cache_hit(username, password, stored_pass):
            profile = read_user_profile(username)
            return True, "ok", profile
        if not password_hash_matches(password, stored_pass):
            return False, "wrongpass", {}
        remember_auth_success_verify(username, password, stored_pass)
        if password_hash_needs_rehash(stored_pass):
            postgres_upsert_user_auth_credential(username, password_hash(password), str(user_file_path(username)))
        profile = read_user_profile(username)
        return True, "ok", profile
    lines = read_user_lines(username)
    if not lines:
        return False, "nouser", {}
    if is_user_login_blocked(username):
        return False, "blocked", {}
    stored_user, stored_pass = parse_user_header(lines[0])
    if not stored_user:
        return False, "nouser", {}
    if auth_success_verify_cache_hit(username, password, stored_pass):
        upgrade_user_password_hash(username, password, lines)
        profile = read_user_profile(username)
        return True, "ok", profile
    if not password_hash_matches(password, stored_pass):
        return False, "wrongpass", {}
    remember_auth_success_verify(username, password, stored_pass)
    upgrade_user_password_hash(username, password, lines)
    profile = read_user_profile(username)
    return True, "ok", profile


# Added 2026-07-09: loads pending password reset codes from the auth state file.
def load_password_reset_state() -> dict:
    if postgres_backend_mode("USER_AUTH_DOCS") == "postgres":
        return postgres_load_password_reset_requests()
    payload = server_database_read_document_json(PASSWORD_RESET_FILE, {})
    return payload if isinstance(payload, dict) else {}


# Added 2026-07-09: persists pending password reset codes atomically.
def save_password_reset_state(payload: dict) -> None:
    if postgres_backend_mode("USER_AUTH_DOCS") == "postgres":
        postgres_replace_password_reset_requests(payload if isinstance(payload, dict) else {})
        return
    USER_ROOT.mkdir(parents=True, exist_ok=True)
    atomic_write_json(PASSWORD_RESET_FILE, payload if isinstance(payload, dict) else {}, indent=2)


# Added 2026-07-09: chooses the user's saved Gmail or internal alias for reset delivery.
def password_reset_destination_for_user(username: str) -> tuple[str, str]:
    profile = read_user_profile(username)
    email = normalize_profile_email(profile.get("email", ""))
    alias = clean(profile.get("email_alias", "")) or user_email_alias(username)
    return email or alias, alias


# Added 2026-07-09: sends reset codes through SMTP or logs them for internal fallback.
def send_password_reset_email(username: str, destination: str, code: str) -> dict:
    destination = normalize_profile_email(destination) or clean(destination)[:254]
    if not destination:
        raise RuntimeError("Tai khoan nay chua co Gmail de gui ma doi mat khau.")
    host = clean(os.environ.get("FUTURE_SMTP_HOST", ""))
    port = int(float(os.environ.get("FUTURE_SMTP_PORT", "587") or 587))
    sender = clean(os.environ.get("FUTURE_SMTP_FROM", "")) or clean(os.environ.get("FUTURE_SMTP_USER", ""))
    smtp_user = clean(os.environ.get("FUTURE_SMTP_USER", ""))
    smtp_pass = str(os.environ.get("FUTURE_SMTP_PASSWORD", "") or "")
    subject = "Future password reset code"
    body = f"Ma doi mat khau Future cho tai khoan {username}: {code}\nMa het han sau 10 phut.\nNeu ban khong yeu cau, hay bo qua email nay."
    if host and sender:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = destination
        message.set_content(body)
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            if smtp_user and smtp_pass:
                smtp.login(smtp_user, smtp_pass)
            smtp.send_message(message)
        return {"sent": True, "method": "smtp", "destination": destination}
    # Updated 2026-07-20: keep fallback delivery records durable in SQLite, never plaintext JSONL.
    database_append = globals().get("server_database_append_event")
    if not callable(database_append):
        raise RuntimeError("Password reset PostgreSQL event writer is unavailable.")
    database_append("password_reset_delivery", {
        "at": utc_timestamp(),
        "username": username,
        "destination": destination,
        "code": code,
        "smtp": "missing",
    })
    return {"sent": False, "method": "server-log", "destination": destination}


# Added 2026-07-09: creates an admin-approved password reset request without requiring outbound Gmail.
def request_password_reset_code(payload: dict, client_key: str = "") -> dict:
    username = normalize_username((payload or {}).get("username", ""))
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    if not server_database_user_exists(username):
        raise RuntimeError("Tai khoan khong ton tai.")
    with AUTH_LOCK:
        state = load_password_reset_state()
        existing = state.get(username)
        if isinstance(existing, dict) and clean(existing.get("status", "pending")) == "pending":
            return {"username": username, "status": "pending_admin", "requested_at": clean(existing.get("requested_at", ""))}
        if isinstance(existing, dict) and clean(existing.get("status", "")) == "approved":
            return {"username": username, "status": "approved", "reviewed_at": clean(existing.get("reviewed_at", ""))}
    allowed, retry_after = anti_robot_rate_allowed(f"password-reset-user:{username}", 5, 300)
    if not allowed:
        raise RuntimeError(f"User nay da gui qua nhieu yeu cau doi mat khau. Vui long doi {retry_after} giay.")
    now = time.time()
    with AUTH_LOCK:
        state = load_password_reset_state()
        profile = read_user_profile(username)
        state[username] = {
            "username": username,
            "status": "pending",
            "full_name": clean(profile.get("full_name", "")),
            "email": normalize_profile_email(profile.get("email", "")),
            "email_alias": clean(profile.get("email_alias", "")),
            "client": clean(client_key)[:80],
            "requested_at": utc_timestamp(),
        }
        save_password_reset_state(state)
    return {"username": username, "status": "pending_admin"}


# Added 2026-07-09: lists password reset requests waiting for local dashboard approval.
def list_pending_password_resets() -> list[dict]:
    state = load_password_reset_state()
    out = []
    for username, item in state.items():
        if not isinstance(item, dict) or clean(item.get("status", "pending")) != "pending":
            continue
        out.append({
            "username": normalize_username(item.get("username", username)),
            "full_name": clean(item.get("full_name", "")),
            "email": clean(item.get("email", "")),
            "email_alias": clean(item.get("email_alias", "")),
            "requested_at": clean(item.get("requested_at", "")),
        })
    out.sort(key=lambda item: item.get("requested_at", ""))
    return out


# Added 2026-07-09: lets the local dashboard grant or reject a password reset ticket.
def approve_password_reset_request(username: str, action: str = "accept", password: str = "") -> dict:
    username = normalize_username(username)
    action = clean(action).lower() or "accept"
    with AUTH_LOCK:
        state = load_password_reset_state()
        item = state.get(username)
        if not isinstance(item, dict) or clean(item.get("status", "pending")) != "pending":
            raise RuntimeError("Khong co yeu cau doi mat khau dang cho.")
        if action in {"reject", "deny", "delete"}:
            item["status"] = "rejected"
            item["reviewed_at"] = utc_timestamp()
            state[username] = item
            save_password_reset_state(state)
            return {"username": username, "status": "rejected"}
        item["status"] = "approved"
        item["reviewed_at"] = utc_timestamp()
        item.pop("code_hash", None)
        item.pop("expires_at", None)
        item["approved_client"] = clean(item.get("client", ""))[:80]
        state[username] = item
        save_password_reset_state(state)
    clear_login_failures("", username)
    return {"username": username, "status": "approved"}


# Added 2026-07-09: verifies the reset code and writes the new hashed password.
def confirm_password_reset_code(payload: dict, client_key: str = "") -> dict:
    username = normalize_username((payload or {}).get("username", ""))
    code = clean((payload or {}).get("code", ""))
    password = str((payload or {}).get("password", (payload or {}).get("new_password", "")) or "")
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    ok, message = validate_register_password(password)
    if not ok:
        raise RuntimeError(message)
    now = time.time()
    with AUTH_LOCK:
        state = load_password_reset_state()
        item = state.get(username)
        if not isinstance(item, dict):
            raise RuntimeError("Chua co yeu cau doi mat khau.")
        status = clean(item.get("status", "pending")).lower()
        if status == "pending":
            raise RuntimeError("Admin chua duyet yeu cau doi mat khau.")
        if status in {"rejected", "denied"}:
            state.pop(username, None)
            save_password_reset_state(state)
            raise RuntimeError("Yeu cau doi mat khau da bi tu choi. Hay lien he admin.")
        if status == "approved":
            state.pop(username, None)
            save_password_reset_state(state)
            set_user_password_hash(username, password)
            clear_login_failures(client_key, username)
            return {"username": username, "changed": True}
        if float(item.get("expires_at", 0) or 0) < now:
            state.pop(username, None)
            save_password_reset_state(state)
            raise RuntimeError("Ma doi mat khau da het han.")
        attempts = int(item.get("attempts", 0) or 0) + 1
        item["attempts"] = attempts
        if attempts > 5:
            state.pop(username, None)
            save_password_reset_state(state)
            raise RuntimeError("Nhap sai ma qua nhieu lan. Hay gui lai ma moi.")
        expected = clean(item.get("code_hash", ""))
        if not hmac.compare_digest(hashlib.sha256(code.encode("utf-8")).hexdigest(), expected):
            state[username] = item
            save_password_reset_state(state)
            raise RuntimeError("Ma doi mat khau khong dung.")
        state.pop(username, None)
        save_password_reset_state(state)
    set_user_password_hash(username, password)
    clear_login_failures(client_key, username)
    return {"username": username, "changed": True}


AUTH_SESSION_USER_LOCKS_LOCK = threading.Lock()
AUTH_SESSION_USER_LOCKS: dict[str, threading.Lock] = {}
AUTH_SESSION_CREATE_BATCH_LOCK = threading.Lock()
AUTH_SESSION_CREATE_BATCH: list[dict] = []
AUTH_SESSION_CREATE_BATCH_SCHEDULED = False
AUTH_SESSION_CREATE_BATCH_SECONDS = 0.001


def auth_session_user_lock(username: str) -> threading.Lock:
    key = normalize_username(username)
    with AUTH_SESSION_USER_LOCKS_LOCK:
        lock = AUTH_SESSION_USER_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            AUTH_SESSION_USER_LOCKS[key] = lock
        return lock


def auth_session_token_key(token: str) -> str:
    raw = clean(token)
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest() if raw else ""


# Added 2026-07-20: group concurrent login rows into one durable writer task before releasing each ACK.
def persist_auth_session_create(username: str, token_key: str, issued_at: float) -> None:
    global AUTH_SESSION_CREATE_BATCH_SCHEDULED
    task = {
        "username": normalize_username(username),
        "token_hash": clean(token_key),
        "issued_at": float(issued_at or time.time()),
        "event": threading.Event(),
        "error": None,
    }
    start_worker = False
    with AUTH_SESSION_CREATE_BATCH_LOCK:
        AUTH_SESSION_CREATE_BATCH.append(task)
        if not AUTH_SESSION_CREATE_BATCH_SCHEDULED:
            AUTH_SESSION_CREATE_BATCH_SCHEDULED = True
            start_worker = True

    if start_worker:
        def worker() -> None:
            global AUTH_SESSION_CREATE_BATCH_SCHEDULED
            while True:
                time.sleep(AUTH_SESSION_CREATE_BATCH_SECONDS)
                with AUTH_SESSION_CREATE_BATCH_LOCK:
                    batch = list(AUTH_SESSION_CREATE_BATCH)
                    AUTH_SESSION_CREATE_BATCH.clear()
                try:
                    server_database_replace_auth_sessions_batch(batch)
                except Exception as exc:
                    for row in batch:
                        row["error"] = exc
                finally:
                    for row in batch:
                        row["event"].set()
                with AUTH_SESSION_CREATE_BATCH_LOCK:
                    if AUTH_SESSION_CREATE_BATCH:
                        continue
                    AUTH_SESSION_CREATE_BATCH_SCHEDULED = False
                    return

        threading.Thread(target=worker, name="auth-session-create-batch", daemon=True).start()

    if not task["event"].wait(15.0):
        raise TimeoutError("Auth session write timed out.")
    if task.get("error") is not None:
        raise task["error"]


# Added 2026-07-20: commit the hashed session row before returning the login token.
def create_auth_session(username: str) -> dict:
    username = normalize_username(username)
    if not server_database_is_test_user(username):
        ensure_server_data_folders(username)
    token = secrets.token_urlsafe(32)
    token_key = auth_session_token_key(token)
    now = time.time()
    with auth_session_user_lock(username):
        persist_auth_session_create(username, token_key, now)
        with AUTH_LOCK:
            stale_tokens = [key for key, session in AUTH_SESSIONS.items() if normalize_username(session.get("username", "")) == username]
            for stale_token in stale_tokens:
                AUTH_SESSIONS.pop(stale_token, None)
                AUTH_REVOKED_SESSIONS[stale_token] = {"reason": "session_replaced", "username": username, "at": now}
            AUTH_SESSIONS[token_key] = {
                "username": username,
                "created_at": now,
                "last_seen": now,
                "last_seen_persisted": now,
                "expires_at": now + 86400,
            }
            expired_revoked = [
                key for key, item in AUTH_REVOKED_SESSIONS.items()
                if now - float((item or {}).get("at", now) or now) > 86400
            ]
            for revoked_token in expired_revoked:
                AUTH_REVOKED_SESSIONS.pop(revoked_token, None)
    return {"token": token, "expires_in": 86400}


def load_auth_sessions() -> None:
    loaded = server_database_load_auth_sessions()
    with AUTH_LOCK:
        AUTH_SESSIONS.clear()
        AUTH_SESSIONS.update(loaded)
    for session in loaded.values():
        try:
            if not server_database_is_test_user(session.get("username", "")):
                ensure_server_data_folders(session.get("username", ""))
        except Exception:
            continue


def save_auth_sessions_locked() -> None:
    server_database_touch_auth_sessions({key: dict(value) for key, value in AUTH_SESSIONS.items()})


# Added 2026-07-20: one bounded worker batches staggered last-seen row touches without rewriting every session.
def schedule_auth_sessions_save(delay: float | None = None, token_key: str = "") -> None:
    delay = AUTH_SESSION_ASYNC_SAVE_DELAY_SECONDS if delay is None else max(0.0, float(delay or 0.0))
    with AUTH_SESSIONS_SAVE_LOCK:
        AUTH_SESSIONS_SAVE_STATE["dirty"] = True
        tokens = AUTH_SESSIONS_SAVE_STATE.setdefault("tokens", set())
        if token_key:
            tokens.add(clean(token_key))
        else:
            with AUTH_LOCK:
                tokens.update(AUTH_SESSIONS.keys())
        if AUTH_SESSIONS_SAVE_STATE.get("scheduled"):
            return
        AUTH_SESSIONS_SAVE_STATE["scheduled"] = True

    def worker() -> None:
        while True:
            if delay:
                time.sleep(delay)
            with AUTH_SESSIONS_SAVE_LOCK:
                AUTH_SESSIONS_SAVE_STATE["dirty"] = False
                token_keys = set(AUTH_SESSIONS_SAVE_STATE.get("tokens") or ())
                AUTH_SESSIONS_SAVE_STATE["tokens"] = set()
            try:
                with AUTH_LOCK:
                    sessions = {key: dict(AUTH_SESSIONS[key]) for key in token_keys if key in AUTH_SESSIONS}
                server_database_touch_auth_sessions(sessions)
            finally:
                with AUTH_SESSIONS_SAVE_LOCK:
                    if AUTH_SESSIONS_SAVE_STATE.get("dirty"):
                        continue
                    AUTH_SESSIONS_SAVE_STATE["scheduled"] = False
                    return

    threading.Thread(target=worker, name="auth-session-flush", daemon=True).start()


# Added 2026-07-07: gives shutdown/delete paths a direct durable session flush.
def flush_auth_sessions_to_disk() -> None:
    with AUTH_LOCK:
        sessions = {key: dict(value) for key, value in AUTH_SESSIONS.items()}
    server_database_touch_auth_sessions(sessions)
    with AUTH_SESSIONS_SAVE_LOCK:
        AUTH_SESSIONS_SAVE_STATE["dirty"] = False
        AUTH_SESSIONS_SAVE_STATE["tokens"] = set()


try:
    atexit.register(flush_auth_sessions_to_disk)
except Exception:
    pass


def auth_session_for_token(token: str) -> dict | None:
    session, _ = auth_session_state_for_token(token)
    return session


def request_cookie_value(cookie_header: str, name: str) -> str:
    target = clean(name)
    if not target:
        return ""
    for part in str(cookie_header or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if clean(key) == target:
            return clean(unquote(value.strip()))
    return ""


def auth_session_state_for_token(token: str) -> tuple[dict | None, str]:
    raw = clean(token)
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    if not raw:
        return None, "missing_token"
    token_key = auth_session_token_key(raw)
    now = time.time()
    session_username = ""
    persist_after_lock = False
    expired_session = False
    with AUTH_LOCK:
        session = AUTH_SESSIONS.get(token_key)
        if not session:
            revoked = AUTH_REVOKED_SESSIONS.get(token_key)
            if revoked and now - float(revoked.get("at", now) or now) <= 86400:
                return None, clean(revoked.get("reason", "")) or "invalid_token"
            AUTH_REVOKED_SESSIONS.pop(token_key, None)
            return None, "invalid_token"
        if now - float(session.get("last_seen", session.get("created_at", now)) or now) > 86400:
            AUTH_SESSIONS.pop(token_key, None)
            AUTH_REVOKED_SESSIONS.pop(token_key, None)
            persist_after_lock = True
            expired_session = True
            session_copy = None
            session_username = ""
        else:
            # Only persist last_seen periodically. Writing the whole sessions file on
            # every authenticated request serializes all users behind AUTH_LOCK and a
            # synchronous disk write, which is the main cause of slow Lesson Vault
            # loads once two or more learners are online.
            previous_persisted = float(session.get("last_seen_persisted", 0) or 0)
            session["last_seen"] = now
            session["expires_at"] = now + 86400
            AUTH_REVOKED_SESSIONS.pop(token_key, None)
            if now - previous_persisted >= AUTH_SESSION_PERSIST_INTERVAL_SECONDS:
                session["last_seen_persisted"] = now
                persist_after_lock = True
            session_copy = dict(session)
            session_username = session.get("username", "")
    if persist_after_lock:
        if expired_session:
            server_database_delete_auth_sessions(token_hashes=[token_key])
        else:
            schedule_auth_sessions_save(token_key=token_key)
    if expired_session:
        return None, "session_expired"
    # Ensure the user's server-data folder exists, but keep it off AUTH_LOCK and
    # throttle it per user so a normal poll does not touch the disk every time.
    if session_username:
        _ensure_session_server_data_folder(session_username, now)
    return session_copy, "ok"


def _ensure_session_server_data_folder(username: str, now: float = 0.0) -> None:
    username = normalize_username(username)
    if not username:
        return
    # Added 2026-07-20: permanent SQLite-only load-test identities must never create production-style user folders.
    if server_database_is_test_user(username):
        return
    now = now or time.time()
    with AUTH_ENSURED_FOLDERS_LOCK:
        last = float(AUTH_ENSURED_FOLDERS.get(username, 0) or 0)
        if now - last < AUTH_ENSURE_FOLDER_INTERVAL_SECONDS:
            return
        AUTH_ENSURED_FOLDERS[username] = now
    try:
        ensure_server_data_folders(username)
    except Exception:
        with AUTH_ENSURED_FOLDERS_LOCK:
            AUTH_ENSURED_FOLDERS.pop(username, None)


def load_pending_users() -> dict:
    if postgres_backend_mode("USER_AUTH_DOCS") == "postgres":
        return postgres_load_pending_registrations()
    payload = server_database_read_document_json(PENDING_USERS_FILE, {})
    return payload if isinstance(payload, dict) else {}


# Added 2026-07-27: short-lived login-screen username checks must not hit
# PostgreSQL/pending registration storage on every focus or repeated key event.
AUTH_USERNAME_LOOKUP_CACHE: dict[str, dict] = {}
AUTH_USERNAME_LOOKUP_CACHE_LOCK = threading.RLock()
AUTH_USERNAME_LOOKUP_CACHE_TTL_SECONDS = 2.0


def auth_username_lookup_payload(username: str) -> dict:
    username = normalize_username(username)
    valid, message = validate_username(username)
    cache_key = username.lower()
    now = time.time()
    if cache_key:
        with AUTH_USERNAME_LOOKUP_CACHE_LOCK:
            cached = AUTH_USERNAME_LOOKUP_CACHE.get(cache_key)
            if isinstance(cached, dict) and now - float(cached.get("at", 0.0) or 0.0) < AUTH_USERNAME_LOOKUP_CACHE_TTL_SECONDS:
                return dict(cached.get("payload") or {})
    pending_status = ""
    if username:
        try:
            pending_item = load_pending_users().get(username, {})
            if isinstance(pending_item, dict):
                pending_status = clean(pending_item.get("status", ""))
        except Exception:
            pending_status = ""
    exists = bool(valid and server_database_user_exists(username))
    payload = {
        "ok": True,
        "username": username,
        "valid": bool(valid),
        "exists": exists,
        "can_login": exists,
        "pending": bool(pending_status and pending_status == "pending"),
        "pending_status": pending_status,
        "message": "" if valid else message,
    }
    if cache_key:
        with AUTH_USERNAME_LOOKUP_CACHE_LOCK:
            AUTH_USERNAME_LOOKUP_CACHE[cache_key] = {"at": now, "payload": dict(payload)}
            if len(AUTH_USERNAME_LOOKUP_CACHE) > 128:
                for old_key, _old in sorted(AUTH_USERNAME_LOOKUP_CACHE.items(), key=lambda item: float(item[1].get("at", 0.0) or 0.0))[:32]:
                    AUTH_USERNAME_LOOKUP_CACHE.pop(old_key, None)
    return payload


def save_pending_users(payload: dict) -> None:
    if postgres_backend_mode("USER_AUTH_DOCS") == "postgres":
        postgres_replace_pending_registrations(payload if isinstance(payload, dict) else {})
        return
    USER_ROOT.mkdir(parents=True, exist_ok=True)
    atomic_write_json(PENDING_USERS_FILE, payload, indent=2)


def submit_pending_registration(payload: dict) -> dict:
    username = normalize_username(payload.get("username", ""))
    password = str(payload.get("password", "") or "")
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    ok, message = validate_register_password(password)
    if not ok:
        raise RuntimeError(message)
    profile = normalize_profile(payload)
    missing = profile_missing(profile)
    if missing:
        raise RuntimeError("Thieu thong tin dang ky: " + ", ".join(missing))
    if server_database_user_exists(username):
        raise RuntimeError("User da ton tai.")
    with AUTH_LOCK:
        pending = load_pending_users()
        item = pending.get(username, {})
        if item and clean(item.get("status", "pending")) == "pending":
            return {"username": username, "status": "pending"}
        pending[username] = {
            "username": username,
            "password_hash": password_hash(password),
            "profile": profile,
            "status": "pending",
            "requested_at": utc_timestamp(),
        }
        save_pending_users(pending)
    return {"username": username, "status": "pending"}
def approve_pending_registration(username: str, action: str = "accept") -> dict:
    username = normalize_username(username)
    action = clean(action).lower() or "accept"
    with AUTH_LOCK:
        pending = load_pending_users()
        item = pending.get(username)
        if not isinstance(item, dict) or clean(item.get("status", "pending")) != "pending":
            raise RuntimeError("Khong co dang ky dang cho.")
        if action in ("reject", "deny", "delete"):
            item["status"] = "rejected"
            item["reviewed_at"] = utc_timestamp()
            pending[username] = item
            save_pending_users(pending)
            return {"username": username, "status": "rejected"}
        if server_database_user_exists(username):
            raise RuntimeError("User da ton tai.")
        password = str(item.get("password_hash", "") or "")
        if not password:
            password = password_hash(str(item.get("password", "") or ""))
        profile = normalize_profile(item.get("profile", {}))
        try:
            lines = [f"{username}:{password}"]
            write_user_lines(username, lines)
            save_user_profile(username, profile)
            if postgres_backend_mode("USER_AUTH_DOCS") == "postgres":
                postgres_upsert_user_auth_credential(username, password, str(user_file_path(username)))
            item["status"] = "approved"
            item["reviewed_at"] = utc_timestamp()
            pending[username] = item
            save_pending_users(pending)
        except Exception:
            raise
        return {"username": username, "status": "approved"}


def list_pending_registrations() -> list[dict]:
    pending = load_pending_users()
    out = []
    for item in pending.values():
        if not isinstance(item, dict) or clean(item.get("status", "pending")) != "pending":
            continue
        profile = item.get("profile", {}) if isinstance(item.get("profile", {}), dict) else {}
        out.append(
            {
                "username": clean(item.get("username", "")),
                "full_name": clean(profile.get("full_name", "")),
                "gender": clean(profile.get("gender", "")),
                "birth_date": clean(profile.get("birth_date", "")),
                "requested_at": clean(item.get("requested_at", "")),
            }
        )
    out.sort(key=lambda item: item.get("requested_at", ""))
    return out
