# Loaded by FUTURE.server_parts.01_core_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def natural_sort_key(value: object = "") -> list[tuple]:
    raw = clean(value).lower()
    parts = re.split(r"(\d+)", raw)
    key: list[tuple] = []
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            key.append((0, int(part), len(part)))
        else:
            key.append((1, part))
    return key


def anti_robot_secret() -> str:
    try:
        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        if ANTI_ROBOT_SECRET_FILE.is_file():
            secret = clean(ANTI_ROBOT_SECRET_FILE.read_text(encoding="utf-8-sig", errors="replace"))
            if len(secret) >= 32:
                return secret
        secret = secrets.token_urlsafe(48)
        atomic_write_text(ANTI_ROBOT_SECRET_FILE, secret, encoding="utf-8")
        return secret
    except Exception:
        return SERVER_STATE.get("started_at", "") + str(os.getpid())


def anti_robot_client_ip(headers, client_address) -> str:
    for name in ("CF-Connecting-IP", "X-Real-IP", "X-Forwarded-For"):
        raw = clean(headers.get(name, ""))
        if raw:
            return clean(raw.split(",", 1)[0])[:80]
    try:
        return clean(client_address[0])[:80]
    except Exception:
        return "unknown"


def anti_robot_rate_allowed(key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
    now = time.time()
    reset_at = now + max(1, window_seconds)
    with ANTI_ROBOT_LOCK:
        stale = [item_key for item_key, item in ANTI_ROBOT_BUCKETS.items() if float(item.get("reset_at", 0) or 0) <= now]
        for item_key in stale[:200]:
            ANTI_ROBOT_BUCKETS.pop(item_key, None)
        bucket = ANTI_ROBOT_BUCKETS.get(key)
        if not bucket or float(bucket.get("reset_at", 0) or 0) <= now:
            ANTI_ROBOT_BUCKETS[key] = {"count": 1, "reset_at": reset_at}
            return True, window_seconds
        bucket["count"] = int(bucket.get("count", 0) or 0) + 1
        return bucket["count"] <= limit, max(1, int(float(bucket.get("reset_at", reset_at)) - now))


def anti_robot_signature(payload: str) -> str:
    return hmac.new(anti_robot_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def make_anti_robot_token(client_key: str = "") -> str:
    issued_at = str(int(time.time()))
    nonce = secrets.token_urlsafe(18)
    payload = f"{issued_at}.{nonce}.{hashlib.sha256(clean(client_key).encode('utf-8')).hexdigest()[:16]}"
    return f"{payload}.{anti_robot_signature(payload)}"


def verify_anti_robot_token(token: str, client_key: str = "") -> tuple[bool, str]:
    parts = clean(token).split(".")
    if len(parts) != 4:
        return False, "missing_challenge"
    issued_at_text, nonce, client_hash, signature = parts
    if not issued_at_text.isdigit() or not nonce or not signature:
        return False, "bad_challenge"
    payload = ".".join(parts[:3])
    expected = anti_robot_signature(payload)
    if not hmac.compare_digest(signature, expected):
        return False, "bad_challenge"
    expected_client_hash = hashlib.sha256(clean(client_key).encode("utf-8")).hexdigest()[:16]
    if client_hash != expected_client_hash:
        return False, "client_changed"
    age = time.time() - int(issued_at_text)
    if age < ANTI_ROBOT_TOKEN_MIN_AGE_SECONDS:
        return False, "challenge_too_fast"
    if age > ANTI_ROBOT_TOKEN_TTL_SECONDS:
        return False, "challenge_expired"
    return True, ""


def anti_robot_browser_like(headers, method: str) -> bool:
    user_agent = clean(headers.get("User-Agent", ""))
    accept = clean(headers.get("Accept", ""))
    if len(user_agent) < 12:
        return False
    if method.upper() == "GET" and accept and "text/html" not in accept and "*/*" not in accept and "application/json" not in accept:
        return False
    return True


# Added 2026-07-09: caches dashboard quota settings briefly so bursts do not reread settings per request.
def user_heavy_quota_limits() -> tuple[int, int]:
    now = time.time()
    with USER_HEAVY_QUOTA_LOCK:
        cached_at = float(USER_HEAVY_QUOTA_SETTINGS_CACHE.get("at", 0) or 0)
        if now - cached_at <= 2:
            return int(USER_HEAVY_QUOTA_SETTINGS_CACHE.get("per_minute", 5) or 5), int(USER_HEAVY_QUOTA_SETTINGS_CACHE.get("min_interval", 5) or 5)
    try:
        settings = load_server_settings()
    except Exception:
        settings = DEFAULT_SETTINGS
    per_minute = max(1, min(120, space_w_int(settings.get("heavy_user_quota_per_minute", DEFAULT_SETTINGS["heavy_user_quota_per_minute"]), DEFAULT_SETTINGS["heavy_user_quota_per_minute"])))
    min_interval = max(0, min(60, space_w_int(settings.get("heavy_user_min_interval_seconds", DEFAULT_SETTINGS["heavy_user_min_interval_seconds"]), DEFAULT_SETTINGS["heavy_user_min_interval_seconds"])))
    with USER_HEAVY_QUOTA_LOCK:
        USER_HEAVY_QUOTA_SETTINGS_CACHE.update({"at": now, "per_minute": per_minute, "min_interval": min_interval})
    return per_minute, min_interval


# Added 2026-07-09: per-user soft quota for expensive AI/OCR/voice routes; light progress saves are intentionally excluded.
def user_heavy_quota_allowed(username: str, group: str = "heavy") -> tuple[bool, int, str]:
    user = normalize_username(username)
    scope = clean(group).lower() or "heavy"
    if not user:
        return True, 0, ""
    per_minute, min_interval = user_heavy_quota_limits()
    now = time.time()
    key = f"{user}:{scope}"
    with USER_HEAVY_QUOTA_LOCK:
        stale = [
            item_key for item_key, item in USER_HEAVY_QUOTA_BUCKETS.items()
            if now - float((item or {}).get("window_start", now) or now) > 180
        ]
        for item_key in stale[:300]:
            USER_HEAVY_QUOTA_BUCKETS.pop(item_key, None)
        bucket = USER_HEAVY_QUOTA_BUCKETS.get(key)
        if not isinstance(bucket, dict) or now - float(bucket.get("window_start", now) or now) >= 60:
            USER_HEAVY_QUOTA_BUCKETS[key] = {"window_start": now, "count": 1, "last_at": now}
            return True, 0, ""
        last_at = float(bucket.get("last_at", 0) or 0)
        if min_interval and now - last_at < min_interval:
            return False, max(1, int(math.ceil(min_interval - (now - last_at)))), "min_interval"
        count = int(bucket.get("count", 0) or 0)
        if count >= per_minute:
            retry = max(1, int(math.ceil(60 - (now - float(bucket.get("window_start", now) or now)))))
            return False, retry, "per_minute"
        bucket["count"] = count + 1
        bucket["last_at"] = now
        return True, 0, ""


def enforce_user_heavy_quota_response(handler, username: str, group: str = "heavy") -> bool:
    try:
        target_path = clean(getattr(handler, "path", "")).split("?", 1)[0]
        if target_path.startswith("/distributed-worker/") or target_path.startswith("/builder/"):
            return True
    except Exception:
        pass
    try:
        if is_admin_user(username):
            return True
    except Exception:
        pass
    ok, retry_after, reason = user_heavy_quota_allowed(username, group)
    if ok:
        return True
    handler.send_json(429, {
        "ok": False,
        "error": "Server busy: tac vu nay dang bi gioi han de tranh spam. Hay thu lai sau vai giay.",
        "reason": f"user_{clean(group).lower() or 'heavy'}_{reason or 'limited'}",
        "retry_after": retry_after,
    })
    return False
