# Loaded by FUTURE.server_parts.02_users_auth_settings into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def normalize_leaderboard_rewards(payload: object = None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    defaults = DEFAULT_SETTINGS["leaderboard_rewards"]
    result = {}
    for scope in ("total", "day", "week", "month"):
        base = defaults.get(scope, {})
        data = source.get(scope) if isinstance(source.get(scope), dict) else {}
        ranks = {}
        raw_ranks = data.get("ranks") if isinstance(data.get("ranks"), dict) else {}
        base_ranks = base.get("ranks") if isinstance(base.get("ranks"), dict) else {}
        for rank in ("1", "2", "3"):
            default_rank = base_ranks.get(rank, {})
            raw_rank = raw_ranks.get(rank) if isinstance(raw_ranks.get(rank), dict) else {}
            try:
                rare = int(float(raw_rank.get("rare", default_rank.get("rare", 0))))
            except Exception:
                rare = int(default_rank.get("rare", 0) or 0)
            try:
                easy = int(float(raw_rank.get("easy", default_rank.get("easy", 0))))
            except Exception:
                easy = int(default_rank.get("easy", 0) or 0)
            common = {}
            alias_map = {
                "space_q": "spaceQ",
                "space_q_silver": "spaceQSilver",
                "space_p": "spaceP",
                "space_p_silver": "spacePSilver",
                "space_s": "spaceS",
                "space_s_silver": "spaceSSilver",
                "space_w": "spaceW",
                "space_w_silver": "spaceWSilver",
                "space_l": "spaceL",
                "space_l_silver": "spaceLSilver",
                "space_v": "spaceV",
            }
            for key in ("space_q", "space_q_silver", "space_p", "space_p_silver", "space_s", "space_s_silver", "space_w", "space_w_silver", "space_l", "space_l_silver", "space_v"):
                alias = alias_map.get(key, key)
                try:
                    common[key] = int(float(raw_rank.get(key, raw_rank.get(alias, default_rank.get(key, 0)))))
                except Exception:
                    common[key] = int(default_rank.get(key, 0) or 0)
                common[key] = max(0, min(9999, common[key]))
            ranks[rank] = {
                "badge": bool(raw_rank.get("badge", default_rank.get("badge", rank == "1"))),
                "rare": max(0, min(9999, rare)),
                "easy": max(0, min(9999, easy)),
                **common,
            }
        result[scope] = {
            "title": clean(data.get("title", base.get("title", scope.title())))[:80] or clean(base.get("title", scope.title())),
            "claim_window": clean(data.get("claim_window", base.get("claim_window", "")))[:180] or clean(base.get("claim_window", "")),
            "ranks": ranks,
        }
    return result


def normalize_leaderboard_reaction_options(payload: object = None) -> list[dict]:
    source = payload if isinstance(payload, list) else DEFAULT_LEADERBOARD_REACTIONS
    result: list[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(source):
        if isinstance(item, dict):
            mark = clean(item.get("mark", item.get("emoji", "")))
            label = clean(item.get("label", ""))
            key = clean(item.get("key", "")).lower()
        else:
            mark = clean(item)
            label = ""
            key = ""
        if not mark:
            continue
        if not label:
            label = mark
        if not key:
            key_seed = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
            key = key_seed or f"reaction-{index + 1}"
        key = re.sub(r"[^a-z0-9_\-]+", "-", key.lower()).strip("-_")[:32] or f"reaction-{index + 1}"
        if key in seen:
            suffix = 2
            base_key = key[:26] or "reaction"
            while f"{base_key}-{suffix}" in seen:
                suffix += 1
            key = f"{base_key}-{suffix}"
        seen.add(key)
        result.append({"key": key, "label": label[:48], "mark": mark[:16]})
        if len(result) >= 12:
            break
    return result or [dict(item) for item in DEFAULT_LEADERBOARD_REACTIONS]


def leaderboard_reaction_options() -> list[dict]:
    try:
        settings = load_server_settings()
        return normalize_leaderboard_reaction_options(settings.get("leaderboard_reactions"))
    except Exception:
        return normalize_leaderboard_reaction_options()


def leaderboard_reaction_key_set() -> set[str]:
    return {clean(item.get("key", "")).lower() for item in leaderboard_reaction_options() if clean(item.get("key", ""))}


def normalize_qm_city_skins(value: object = None) -> list[dict]:
    source = value if isinstance(value, list) else DEFAULT_QM_CITY_SKINS
    rows: list[dict] = []
    for index, item in enumerate(source):
        data = item if isinstance(item, dict) else {}
        name = clean(data.get("name") or data.get("title") or f"Skin {index + 1}")[:80]
        if not name:
            continue
        skin_id = re.sub(r"[^a-z0-9_.-]+", "-", clean(data.get("id") or name).lower()).strip("-")[:64] or f"skin-{index + 1}"
        try:
            price = int(float(data.get("price", data.get("cost", 50)) or 50))
        except Exception:
            price = 50
        rows.append({
            "id": skin_id,
            "name": name,
            "price": max(0, min(999999, price)),
            "image": clean(data.get("image") or data.get("image_url") or data.get("imageUrl") or "")[:600],
            "description": clean(data.get("description") or data.get("desc") or "")[:300],
        })
    if not rows:
        rows = [dict(item) for item in DEFAULT_QM_CITY_SKINS]
    return rows[:24]


def normalize_qm_city_levels(value: object = None) -> list[dict]:
    source = value if isinstance(value, list) and value else DEFAULT_QM_CITY_LEVELS
    rows: list[dict] = []
    seen: set[int] = set()
    for index, item in enumerate(source):
        data = item if isinstance(item, dict) else {}
        try:
            level = int(float(data.get("level", data.get("lvl", index + 1)) or index + 1))
        except Exception:
            level = index + 1
        try:
            total_exp = int(float(data.get("total_exp", data.get("totalExp", data.get("exp", data.get("xp", 0)))) or 0))
        except Exception:
            total_exp = 0
        level = max(1, min(999, level))
        total_exp = max(0, min(100000000, total_exp))
        if level in seen:
            continue
        seen.add(level)
        rows.append({"level": level, "total_exp": total_exp})
    if not rows:
        rows = [dict(item) for item in DEFAULT_QM_CITY_LEVELS]
    if not any(int(row.get("level", 0) or 0) == 1 for row in rows):
        rows.append({"level": 1, "total_exp": 0})
    rows.sort(key=lambda row: int(row.get("level", 1) or 1))
    normalized = []
    previous_exp = 0
    for row in rows[:100]:
        level = int(row.get("level", 1) or 1)
        total_exp = max(previous_exp, int(row.get("total_exp", 0) or 0))
        if level == 1:
            total_exp = 0
        normalized.append({"level": level, "total_exp": total_exp})
        previous_exp = total_exp
    return normalized


def normalize_qm_city_npc_mode(source: dict, default_enabled: bool = True) -> str:
    raw_mode = clean(
        source.get(
            "mode",
            source.get("source_mode", source.get("sourceMode", source.get("npc_mode", source.get("npcMode", "")))),
        )
    ).lower()
    if raw_mode in {"mixed", "mix", "all", "both", "top+city", "city+top"}:
        return "mixed"
    if raw_mode in {"city", "citizen", "citizens", "resident", "residents", "off", "default"}:
        return "city"
    if raw_mode in {"top", "tops", "racer", "racers", "npc_top", "npc-top", "on"}:
        return "top"
    enabled = truthy(source.get("enabled", source.get("qm_city_npc_enabled", default_enabled)), bool(default_enabled))
    return "top" if enabled else "city"


def normalize_qm_city_npc_settings(value: object = None) -> dict:
    defaults = DEFAULT_SETTINGS.get("qm_city_npc", {})
    source = value if isinstance(value, dict) else {}

    def read_int(key: str, fallback: int, minimum: int, maximum: int, *aliases: str) -> int:
        raw = source.get(key, None)
        if raw is None:
            for alias in aliases:
                if alias in source:
                    raw = source.get(alias)
                    break
        if raw is None:
            raw = fallback
        try:
            number = int(float(raw))
        except Exception:
            number = int(fallback)
        return max(int(minimum), min(int(maximum), number))

    mode = normalize_qm_city_npc_mode(source, bool(defaults.get("enabled", True)))
    enabled = mode != "city"
    min_active = read_int("min_active", defaults.get("min_active", 1), 0, 5, "minActive", "qm_city_npc_min_active")
    max_active = read_int("max_active", defaults.get("max_active", 5), 1, 8, "maxActive", "qm_city_npc_max_active")
    if max_active < min_active:
        max_active = min_active
    online_min = read_int("online_min_minutes", defaults.get("online_min_minutes", 20), 5, 180, "onlineMinMinutes", "qm_city_npc_online_min_minutes")
    online_max = read_int("online_max_minutes", defaults.get("online_max_minutes", 40), 5, 240, "onlineMaxMinutes", "qm_city_npc_online_max_minutes")
    if online_max < online_min:
        online_max = online_min
    invite_min = read_int("invite_cooldown_min_seconds", defaults.get("invite_cooldown_min_seconds", 70), 15, 900, "inviteCooldownMinSeconds")
    invite_max = read_int("invite_cooldown_max_seconds", defaults.get("invite_cooldown_max_seconds", 180), 20, 1200, "inviteCooldownMaxSeconds")
    if invite_max < invite_min:
        invite_max = invite_min
    return {
        "enabled": bool(enabled),
        "mode": mode,
        "spawn_chance_percent": read_int("spawn_chance_percent", defaults.get("spawn_chance_percent", 55), 0, 100, "spawnChancePercent", "qm_city_npc_spawn_chance_percent"),
        "min_active": min_active,
        "max_active": max_active,
        "online_min_minutes": online_min,
        "online_max_minutes": online_max,
        "answer_correct_percent": read_int("answer_correct_percent", defaults.get("answer_correct_percent", 58), 0, 100, "answerCorrectPercent", "qm_city_npc_answer_correct_percent"),
        "steal_correct_percent": read_int("steal_correct_percent", defaults.get("steal_correct_percent", 34), 0, 100, "stealCorrectPercent", "qm_city_npc_steal_correct_percent"),
        "invite_chance_percent": read_int("invite_chance_percent", defaults.get("invite_chance_percent", 8), 0, 100, "inviteChancePercent", "qm_city_npc_invite_chance_percent"),
        "invite_cooldown_min_seconds": invite_min,
        "invite_cooldown_max_seconds": invite_max,
    }


def split_webrtc_ice_urls(value: object = None) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, tuple):
        raw_items = list(value)
    else:
        raw_text = str(value or "").strip()
        if not raw_text:
            raw_items = []
        else:
            raw_items = re.split(r"[\s,;|]+", raw_text)
    urls: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        raw = str(item or "").strip()
        if not raw:
            continue
        lower = raw.lower()
        if not (lower.startswith("stun:") or lower.startswith("turn:") or lower.startswith("turns:")):
            continue
        raw = raw[:320]
        key = raw.lower()
        if key in seen:
            continue
        seen.add(key)
        urls.append(raw)
        if len(urls) >= 16:
            break
    return urls


def normalize_webrtc_ice_servers(value: object = None) -> list[dict]:
    source = value if isinstance(value, list) else [value]
    servers: list[dict] = []
    seen: set[str] = set()
    for item in source:
        if isinstance(item, dict):
            urls = split_webrtc_ice_urls(item.get("urls", item.get("url", "")))
            username = clean(item.get("username", ""))[:160]
            credential = str(item.get("credential", item.get("password", "")) or "")[:260]
        else:
            urls = split_webrtc_ice_urls(item)
            username = ""
            credential = ""
        if not urls:
            continue
        key = "|".join(url.lower() for url in urls)
        if key in seen:
            continue
        seen.add(key)
        row = {"urls": urls}
        if username:
            row["username"] = username
        if credential:
            row["credential"] = credential
        servers.append(row)
        if len(servers) >= 12:
            break
    return servers


def webrtc_env_ice_servers() -> list[dict]:
    rows: list[dict] = []
    raw_json = str(os.environ.get("FUTURE_WEBRTC_ICE_SERVERS", "") or "").strip()
    if raw_json:
        try:
            parsed = json.loads(raw_json)
        except Exception:
            parsed = raw_json
        rows.extend(normalize_webrtc_ice_servers(parsed))
    turn_urls = split_webrtc_ice_urls(os.environ.get("FUTURE_TURN_URLS", ""))
    if turn_urls:
        row = {"urls": turn_urls}
        username = clean(os.environ.get("FUTURE_TURN_USERNAME", ""))[:160]
        credential = str(os.environ.get("FUTURE_TURN_CREDENTIAL", "") or "")[:260]
        if username:
            row["username"] = username
        if credential:
            row["credential"] = credential
        rows.extend(normalize_webrtc_ice_servers([row]))
    return rows


def webrtc_turn_servers_from_settings(source: dict | None = None) -> list[dict]:
    source = source if isinstance(source, dict) else {}
    turn_urls = split_webrtc_ice_urls(source.get("turn_urls", source.get("turnUrls", "")))
    if not turn_urls:
        return []
    row = {"urls": turn_urls}
    username = clean(source.get("turn_username", source.get("turnUsername", "")))[:160]
    credential = str(source.get("turn_credential", source.get("turnCredential", source.get("turn_password", ""))) or "")[:260]
    if username:
        row["username"] = username
    if credential:
        row["credential"] = credential
    return normalize_webrtc_ice_servers([row])


def merge_webrtc_ice_servers(*groups: object) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for group in groups:
        for server in normalize_webrtc_ice_servers(group):
            urls = server.get("urls", [])
            key = "|".join(str(url).lower() for url in urls)
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(server)
            if len(merged) >= 12:
                return merged
    return merged


def webrtc_ice_servers_have_turn(servers: object = None) -> bool:
    for server in normalize_webrtc_ice_servers(servers):
        for url in server.get("urls", []):
            lower = str(url or "").lower()
            if lower.startswith("turn:") or lower.startswith("turns:"):
                return True
    return False


CLOUDFLARE_TURN_API_BASE = "https://rtc.live.cloudflare.com/v1/turn/keys"
CLOUDFLARE_TURN_CREDENTIAL_TTL = 86400
CLOUDFLARE_TURN_REFRESH_MARGIN = 900
_CLOUDFLARE_TURN_LOCK = threading.RLock()
_CLOUDFLARE_TURN_CACHE: dict = {"key": "", "servers": [], "expires_at": 0.0, "fetched_at": 0.0, "error": ""}


def cloudflare_turn_credentials_config(settings: dict | None = None) -> tuple[str, str]:
    """Read the long-lived Cloudflare Realtime TURN key id + API token.

    Env vars win over the settings file. The API token never leaves the server.
    """
    source = settings if isinstance(settings, dict) else {}
    key_id = clean(os.environ.get("FUTURE_CLOUDFLARE_TURN_KEY_ID", "")) or clean(
        source.get("cloudflare_turn_key_id", source.get("cloudflareTurnKeyId", ""))
    )
    api_token = str(os.environ.get("FUTURE_CLOUDFLARE_TURN_API_TOKEN", "") or "").strip() or str(
        source.get("cloudflare_turn_api_token", source.get("cloudflareTurnApiToken", "")) or ""
    ).strip()
    return key_id[:120], api_token[:240]


def cloudflare_turn_ice_servers(settings: dict | None = None) -> list[dict]:
    """Return short-lived Cloudflare TURN ICE servers, cached until near expiry.

    Calls the Cloudflare Realtime generate-ice-servers endpoint with the
    server-side token and hands back only the ephemeral username/credential.
    Falls back to the cached value (or empty list) when the API call fails.
    """
    key_id, api_token = cloudflare_turn_credentials_config(settings)
    if not key_id or not api_token:
        return []
    cache_key = hashlib.sha256(f"{key_id}:{api_token}".encode("utf-8")).hexdigest()
    now = time.time()
    with _CLOUDFLARE_TURN_LOCK:
        cached = _CLOUDFLARE_TURN_CACHE
        if (
            cached.get("key") == cache_key
            and cached.get("servers")
            and float(cached.get("expires_at", 0) or 0) - now > CLOUDFLARE_TURN_REFRESH_MARGIN
        ):
            return [dict(server) for server in cached["servers"]]
    url = f"{CLOUDFLARE_TURN_API_BASE}/{quote(key_id, safe='')}/credentials/generate-ice-servers"
    body = json.dumps({"ttl": CLOUDFLARE_TURN_CREDENTIAL_TTL}).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        request = Request(url, data=body, headers=headers, method="POST")
        with urlopen(request, timeout=12) as response:
            raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw) if raw else {}
        ice = parsed.get("iceServers", parsed.get("ice_servers", parsed)) if isinstance(parsed, dict) else parsed
        servers = normalize_webrtc_ice_servers(ice if isinstance(ice, list) else [ice])
        filtered_servers: list[dict] = []
        for server in servers:
            urls = [url for url in server.get("urls", []) if ":53" not in str(url or "")]
            if not urls:
                continue
            row = {"urls": urls}
            if server.get("username"):
                row["username"] = server.get("username")
            if server.get("credential"):
                row["credential"] = server.get("credential")
            filtered_servers.append(row)
        servers = normalize_webrtc_ice_servers(filtered_servers)
    except Exception as exc:
        with _CLOUDFLARE_TURN_LOCK:
            stale = _CLOUDFLARE_TURN_CACHE
            _CLOUDFLARE_TURN_CACHE["error"] = str(exc)[:200]
            if (
                stale.get("key") == cache_key
                and stale.get("servers")
                and float(stale.get("expires_at", 0) or 0) > now
            ):
                return [dict(server) for server in stale["servers"]]
        return []
    if not servers:
        return []
    with _CLOUDFLARE_TURN_LOCK:
        _CLOUDFLARE_TURN_CACHE.update(
            {
                "key": cache_key,
                "servers": [dict(server) for server in servers],
                "expires_at": now + CLOUDFLARE_TURN_CREDENTIAL_TTL,
                "fetched_at": now,
                "error": "",
            }
        )
    return [dict(server) for server in servers]


# Added 2026-07-07: normalizes dashboard-controlled distributed worker lane caps.
def normalize_distributed_worker_job_limits(value) -> dict:
    defaults = DEFAULT_SETTINGS.get("distributed_worker_job_limits", {})
    source = value if isinstance(value, dict) else {}
    result: dict[str, int] = {}
    for kind in ("translate", "tts", "stt", "gemini", "phonemize"):
        try:
            raw = source.get(kind, defaults.get(kind, 1))
            amount = int(float(raw))
        except Exception:
            amount = int(defaults.get(kind, 1) or 1)
        result[kind] = max(0, min(64, amount))
    return result


# Added 2026-07-07: normalizes how many worker clients one machine should run.
def normalize_distributed_worker_machine_limit(value) -> int:
    try:
        amount = int(float(value))
    except Exception:
        amount = int(DEFAULT_SETTINGS.get("distributed_worker_machine_limit", 1) or 1)
    return max(1, min(32, amount))


def normalize_server_settings(payload: dict | None = None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    try:
        seconds = int(float(source.get("word_hint_cycle_seconds", DEFAULT_SETTINGS["word_hint_cycle_seconds"])))
    except Exception:
        seconds = DEFAULT_SETTINGS["word_hint_cycle_seconds"]
    seconds = max(5, min(180, seconds))
    try:
        paragraph_seconds = int(float(source.get("paragraph_hint_seconds", DEFAULT_SETTINGS["paragraph_hint_seconds"])))
    except Exception:
        paragraph_seconds = DEFAULT_SETTINGS["paragraph_hint_seconds"]
    paragraph_seconds = max(3, min(300, paragraph_seconds))
    try:
        chat_limit_mb = int(float(source.get("chat_attachment_limit_mb", DEFAULT_SETTINGS["chat_attachment_limit_mb"])))
    except Exception:
        chat_limit_mb = DEFAULT_SETTINGS["chat_attachment_limit_mb"]
    chat_limit_mb = max(1, min(4096, chat_limit_mb))
    ai_agent_notice_voice = clean(source.get("ai_agent_notice_voice", source.get("aiAgentNoticeVoice", DEFAULT_SETTINGS["ai_agent_notice_voice"])))
    if not ai_agent_notice_voice:
        ai_agent_notice_voice = DEFAULT_SETTINGS["ai_agent_notice_voice"]
    ai_agent_notice_voice = ai_agent_notice_voice[:160]
    space_w_ai_check_voice_enabled = truthy(
        source.get(
            "space_w_ai_check_voice_enabled",
            source.get("spaceWAiCheckVoiceEnabled", DEFAULT_SETTINGS["space_w_ai_check_voice_enabled"]),
        ),
        DEFAULT_SETTINGS["space_w_ai_check_voice_enabled"],
    )
    try:
        cpu_threshold = int(float(source.get("cpu_queue_threshold_percent", source.get("cpuQueueThresholdPercent", DEFAULT_SETTINGS["cpu_queue_threshold_percent"]))))
    except Exception:
        cpu_threshold = DEFAULT_SETTINGS["cpu_queue_threshold_percent"]
    cpu_threshold = max(45, min(98, cpu_threshold))
    try:
        heavy_quota_per_minute = int(float(source.get("heavy_user_quota_per_minute", source.get("heavyUserQuotaPerMinute", DEFAULT_SETTINGS["heavy_user_quota_per_minute"]))))
    except Exception:
        heavy_quota_per_minute = DEFAULT_SETTINGS["heavy_user_quota_per_minute"]
    heavy_quota_per_minute = max(1, min(120, heavy_quota_per_minute))
    try:
        heavy_min_interval_seconds = int(float(source.get("heavy_user_min_interval_seconds", source.get("heavyUserMinIntervalSeconds", DEFAULT_SETTINGS["heavy_user_min_interval_seconds"]))))
    except Exception:
        heavy_min_interval_seconds = DEFAULT_SETTINGS["heavy_user_min_interval_seconds"]
    heavy_min_interval_seconds = max(0, min(60, heavy_min_interval_seconds))
    # Added 2026-07-07: lets the server dashboard cap distributed worker lanes before falling back to local work.
    distributed_worker_job_limits = normalize_distributed_worker_job_limits(
        source.get("distributed_worker_job_limits", source.get("distributedWorkerJobLimits", DEFAULT_SETTINGS["distributed_worker_job_limits"]))
    )
    distributed_worker_machine_limit = normalize_distributed_worker_machine_limit(
        source.get(
            "distributed_worker_machine_limit",
            source.get("distributedWorkerMachineLimit", DEFAULT_SETTINGS.get("distributed_worker_machine_limit", 1)),
        )
    )
    try:
        qm_city_min_english = int(float(source.get("qm_city_chat_min_english_percent", source.get("qmCityChatMinEnglishPercent", DEFAULT_SETTINGS["qm_city_chat_min_english_percent"]))))
    except Exception:
        qm_city_min_english = DEFAULT_SETTINGS["qm_city_chat_min_english_percent"]
    qm_city_min_english = max(1, min(100, qm_city_min_english))
    try:
        qm_city_invalid_run = int(float(source.get("qm_city_chat_invalid_run_limit", source.get("qmCityChatInvalidRunLimit", DEFAULT_SETTINGS["qm_city_chat_invalid_run_limit"]))))
    except Exception:
        qm_city_invalid_run = DEFAULT_SETTINGS["qm_city_chat_invalid_run_limit"]
    qm_city_invalid_run = max(1, min(20, qm_city_invalid_run))
    qm_city_skins = normalize_qm_city_skins(source.get("qm_city_skins", source.get("qmCitySkins", DEFAULT_SETTINGS["qm_city_skins"])))
    qm_city_levels = normalize_qm_city_levels(source.get("qm_city_levels", source.get("qmCityLevels", DEFAULT_SETTINGS["qm_city_levels"])))
    qm_city_npc = normalize_qm_city_npc_settings(source.get("qm_city_npc", source.get("qmCityNpc", DEFAULT_SETTINGS["qm_city_npc"])))
    cpu_guard_enabled = truthy(source.get("cpu_guard_enabled", source.get("cpuGuardEnabled", DEFAULT_SETTINGS["cpu_guard_enabled"])), DEFAULT_SETTINGS["cpu_guard_enabled"])
    raw_hud = source.get("question_hud_lines", DEFAULT_SETTINGS["question_hud_lines"])
    if isinstance(raw_hud, str):
        hud_lines = [clean(item) for item in re.split(r"[\r\n|;]+", raw_hud)]
    elif isinstance(raw_hud, list):
        hud_lines = [clean(item) for item in raw_hud]
    else:
        hud_lines = []
    hud_lines = [item for item in hud_lines if item][:4]
    if not hud_lines:
        hud_lines = list(DEFAULT_SETTINGS["question_hud_lines"])
    public_hostname = normalize_cloudflare_public_hostname(source.get("cloudflare_public_hostname", DEFAULT_SETTINGS["cloudflare_public_hostname"]))
    tunnel_name = normalize_cloudflare_tunnel_name(source.get("cloudflare_tunnel_name", DEFAULT_SETTINGS["cloudflare_tunnel_name"]))
    cloudflare_turn_key_id = clean(source.get("cloudflare_turn_key_id", source.get("cloudflareTurnKeyId", "")))[:120]
    cloudflare_turn_api_token = str(source.get("cloudflare_turn_api_token", source.get("cloudflareTurnApiToken", "")) or "").strip()[:240]
    webrtc_ice_servers = merge_webrtc_ice_servers(
        DEFAULT_SETTINGS["webrtc_ice_servers"],
        source.get("webrtc_ice_servers", source.get("webrtcIceServers", [])),
        webrtc_turn_servers_from_settings(source),
        webrtc_env_ice_servers(),
    ) or normalize_webrtc_ice_servers(DEFAULT_SETTINGS["webrtc_ice_servers"])
    webrtc_force_relay = truthy(
        source.get(
            "webrtc_force_relay",
            source.get("webrtcForceRelay", DEFAULT_SETTINGS["webrtc_force_relay"]),
        ),
        DEFAULT_SETTINGS["webrtc_force_relay"],
    )
    if truthy(os.environ.get("FUTURE_WEBRTC_FORCE_RELAY", ""), False):
        webrtc_force_relay = True
    secret_hash = clean(source.get("hosted_client_secret_hash", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", secret_hash.lower()):
        secret_hash = ""
    secret_hash = secret_hash.lower()
    raw_secret = str(source.get("hosted_client_secret", "") or "")
    if raw_secret:
        secret_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
    updated_at = clean(source.get("updated_at", "")) if isinstance(source, dict) else ""
    return {
        "word_hint_cycle_seconds": seconds,
        "word_hint_cycle_ms": seconds * 1000,
        "paragraph_hint_seconds": paragraph_seconds,
        "paragraph_hint_ms": paragraph_seconds * 1000,
        "chat_attachment_limit_mb": chat_limit_mb,
        "chat_attachment_limit_bytes": chat_limit_mb * 1024 * 1024,
        "ai_agent_notice_voice": ai_agent_notice_voice,
        "space_w_ai_check_voice_enabled": bool(space_w_ai_check_voice_enabled),
        "cpu_guard_enabled": bool(cpu_guard_enabled),
        "cpu_queue_threshold_percent": cpu_threshold,
        "heavy_user_quota_per_minute": heavy_quota_per_minute,
        "heavy_user_min_interval_seconds": heavy_min_interval_seconds,
        "distributed_worker_job_limits": distributed_worker_job_limits,
        "distributed_worker_machine_limit": distributed_worker_machine_limit,
        "qm_city_chat_min_english_percent": qm_city_min_english,
        "qm_city_chat_invalid_run_limit": qm_city_invalid_run,
        "qm_city_skins": qm_city_skins,
        "qm_city_levels": qm_city_levels,
        "qm_city_npc": qm_city_npc,
        "cloudflare_public_hostname": public_hostname,
        "cloudflare_tunnel_name": tunnel_name,
        "cloudflare_turn_key_id": cloudflare_turn_key_id,
        "cloudflare_turn_api_token": cloudflare_turn_api_token,
        "webrtc_ice_servers": webrtc_ice_servers,
        "webrtc_force_relay": bool(webrtc_force_relay),
        "webrtc_has_turn": webrtc_ice_servers_have_turn(webrtc_ice_servers),
        "turn_urls": split_webrtc_ice_urls(source.get("turn_urls", source.get("turnUrls", ""))),
        "turn_username": clean(source.get("turn_username", source.get("turnUsername", "")))[:160],
        "turn_credential": str(source.get("turn_credential", source.get("turnCredential", source.get("turn_password", ""))) or "")[:260],
        "turn_credential_type": "password",
        "webrtc_relay_only": bool(webrtc_force_relay),
        "question_hud_lines": hud_lines,
        "question_hud_text": "\n".join(hud_lines),
        "hosted_client_secret_hash": secret_hash,
        "hosted_client_secret_set": bool(secret_hash),
        "leaderboard_reactions": normalize_leaderboard_reaction_options(source.get("leaderboard_reactions", DEFAULT_SETTINGS["leaderboard_reactions"])),
        "leaderboard_rewards": normalize_leaderboard_rewards(source.get("leaderboard_rewards", DEFAULT_SETTINGS["leaderboard_rewards"])),
        "updated_at": updated_at,
    }


def public_server_settings(payload: dict | None = None) -> dict:
    settings = payload if isinstance(payload, dict) else load_server_settings()
    base_ice_servers = normalize_webrtc_ice_servers(settings.get("webrtc_ice_servers", DEFAULT_SETTINGS["webrtc_ice_servers"]))
    cloudflare_ice_servers = cloudflare_turn_ice_servers(settings)
    if cloudflare_ice_servers:
        base_stun_only_servers: list[dict] = []
        for server in base_ice_servers:
            urls = [url for url in server.get("urls", []) if str(url or "").lower().startswith("stun:")]
            if not urls:
                continue
            base_stun_only_servers.append({"urls": urls})
        public_ice_servers = merge_webrtc_ice_servers(cloudflare_ice_servers, base_stun_only_servers)
    else:
        public_ice_servers = base_ice_servers
    public_has_turn = webrtc_ice_servers_have_turn(public_ice_servers)
    public_turn_urls: list[str] = []
    public_turn_username = clean(settings.get("turn_username", ""))[:160]
    public_turn_credential_set = bool(settings.get("turn_credential", ""))
    for server in public_ice_servers:
        urls = [str(url or "") for url in server.get("urls", []) if str(url or "").lower().startswith(("turn:", "turns:"))]
        if not urls:
            continue
        public_turn_urls.extend(urls)
        if server.get("username"):
            public_turn_username = clean(server.get("username", ""))[:160]
        if server.get("credential"):
            public_turn_credential_set = True
    return {
        "word_hint_cycle_seconds": settings.get("word_hint_cycle_seconds", DEFAULT_SETTINGS["word_hint_cycle_seconds"]),
        "word_hint_cycle_ms": settings.get("word_hint_cycle_ms", DEFAULT_SETTINGS["word_hint_cycle_seconds"] * 1000),
        "paragraph_hint_seconds": settings.get("paragraph_hint_seconds", DEFAULT_SETTINGS["paragraph_hint_seconds"]),
        "paragraph_hint_ms": settings.get("paragraph_hint_ms", DEFAULT_SETTINGS["paragraph_hint_seconds"] * 1000),
        "chat_attachment_limit_mb": settings.get("chat_attachment_limit_mb", DEFAULT_SETTINGS["chat_attachment_limit_mb"]),
        "chat_attachment_limit_bytes": settings.get("chat_attachment_limit_bytes", DEFAULT_SETTINGS["chat_attachment_limit_mb"] * 1024 * 1024),
        "ai_agent_notice_voice": clean(settings.get("ai_agent_notice_voice", DEFAULT_SETTINGS["ai_agent_notice_voice"])),
        "space_w_ai_check_voice_enabled": bool(settings.get("space_w_ai_check_voice_enabled", DEFAULT_SETTINGS["space_w_ai_check_voice_enabled"])),
        "cpu_guard_enabled": bool(settings.get("cpu_guard_enabled", DEFAULT_SETTINGS["cpu_guard_enabled"])),
        "cpu_queue_threshold_percent": max(45, min(98, space_w_int(settings.get("cpu_queue_threshold_percent", DEFAULT_SETTINGS["cpu_queue_threshold_percent"]), DEFAULT_SETTINGS["cpu_queue_threshold_percent"]))),
        "heavy_user_quota_per_minute": max(1, min(120, space_w_int(settings.get("heavy_user_quota_per_minute", DEFAULT_SETTINGS["heavy_user_quota_per_minute"]), DEFAULT_SETTINGS["heavy_user_quota_per_minute"]))),
        "heavy_user_min_interval_seconds": max(0, min(60, space_w_int(settings.get("heavy_user_min_interval_seconds", DEFAULT_SETTINGS["heavy_user_min_interval_seconds"]), DEFAULT_SETTINGS["heavy_user_min_interval_seconds"]))),
        "distributed_worker_job_limits": normalize_distributed_worker_job_limits(settings.get("distributed_worker_job_limits", DEFAULT_SETTINGS["distributed_worker_job_limits"])),
        "distributed_worker_machine_limit": normalize_distributed_worker_machine_limit(settings.get("distributed_worker_machine_limit", DEFAULT_SETTINGS.get("distributed_worker_machine_limit", 1))),
        "qm_city_chat_min_english_percent": max(1, min(100, space_w_int(settings.get("qm_city_chat_min_english_percent", DEFAULT_SETTINGS["qm_city_chat_min_english_percent"]), DEFAULT_SETTINGS["qm_city_chat_min_english_percent"]))),
        "qm_city_chat_invalid_run_limit": max(1, min(20, space_w_int(settings.get("qm_city_chat_invalid_run_limit", DEFAULT_SETTINGS["qm_city_chat_invalid_run_limit"]), DEFAULT_SETTINGS["qm_city_chat_invalid_run_limit"]))),
        "qm_city_skins": normalize_qm_city_skins(settings.get("qm_city_skins", DEFAULT_SETTINGS["qm_city_skins"])),
        "qm_city_levels": normalize_qm_city_levels(settings.get("qm_city_levels", DEFAULT_SETTINGS["qm_city_levels"])),
        "qm_city_npc": normalize_qm_city_npc_settings(settings.get("qm_city_npc", DEFAULT_SETTINGS["qm_city_npc"])),
        "cloudflare_public_hostname": clean(settings.get("cloudflare_public_hostname", DEFAULT_SETTINGS["cloudflare_public_hostname"])),
        "cloudflare_tunnel_name": clean(settings.get("cloudflare_tunnel_name", DEFAULT_SETTINGS["cloudflare_tunnel_name"])),
        "cloudflare_custom_domain_enabled": bool(clean(settings.get("cloudflare_public_hostname", ""))),
        "webrtc_ice_servers": public_ice_servers,
        "webrtc_force_relay": bool(settings.get("webrtc_force_relay", DEFAULT_SETTINGS["webrtc_force_relay"])),
        "webrtc_has_turn": public_has_turn,
        "turn_urls": split_webrtc_ice_urls(public_turn_urls),
        "turn_username": public_turn_username,
        "turn_credential_set": public_turn_credential_set,
        "webrtc_relay_only": bool(settings.get("webrtc_force_relay", DEFAULT_SETTINGS["webrtc_force_relay"])),
        "webrtc": {
            "ice_servers": public_ice_servers,
            "force_relay": bool(settings.get("webrtc_force_relay", DEFAULT_SETTINGS["webrtc_force_relay"])),
            "has_turn": public_has_turn,
            "cloudflare_turn": bool(cloudflare_ice_servers),
        },
        "question_hud_lines": list(settings.get("question_hud_lines", DEFAULT_SETTINGS["question_hud_lines"]) or []),
        "question_hud_text": clean(settings.get("question_hud_text", "")),
        "hosted_client_secret_set": bool(settings.get("hosted_client_secret_hash", "")),
        "hosted_client_obfuscation": "password" if settings.get("hosted_client_secret_hash", "") else "default",
        "leaderboard_reactions": normalize_leaderboard_reaction_options(settings.get("leaderboard_reactions", DEFAULT_SETTINGS["leaderboard_reactions"])),
        "leaderboard_rewards": normalize_leaderboard_rewards(settings.get("leaderboard_rewards", DEFAULT_SETTINGS["leaderboard_rewards"])),
        "updated_at": clean(settings.get("updated_at", "")),
    }


# Added 2026-07-20: public settings are immutable bytes until the SQLite settings document changes.
def public_server_settings_response_cache_row() -> dict:
    if str(os.environ.get("FUTURE_POSTGRES_ONLY", "") or "").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            stat = SETTINGS_FILE.stat()
            signature = f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}"
        except Exception:
            signature = "missing"
    else:
        signature = server_database_document_signature(SETTINGS_FILE)
    cache = globals().setdefault("PUBLIC_SERVER_SETTINGS_RESPONSE_CACHE", {})
    lock = globals().setdefault("PUBLIC_SERVER_SETTINGS_RESPONSE_CACHE_LOCK", threading.RLock())
    with lock:
        row = cache.get("row") if isinstance(cache, dict) else None
        if isinstance(row, dict) and row.get("signature") == signature and isinstance(row.get("bytes"), bytes):
            return {**row, "cache_hit": True}
    payload = {"ok": True, **public_server_settings()}
    data = json_bytes(payload)
    row = {
        "signature": signature,
        "payload": payload,
        "bytes": data,
        "etag": f'"settings-{hashlib.sha1(data).hexdigest()}"',
        "at": time.time(),
        "cache_hit": False,
    }
    with lock:
        cache["row"] = row
    return row


def load_server_settings() -> dict:
    with SETTINGS_LOCK:
        if str(os.environ.get("FUTURE_POSTGRES_ONLY", "") or "").strip().lower() in {"1", "true", "yes", "on"}:
            try:
                if SETTINGS_FILE.is_file():
                    payload = json.loads(SETTINGS_FILE.read_text(encoding="utf-8-sig"))
                else:
                    payload = None
            except Exception:
                payload = None
        else:
            payload = server_database_read_document_json(SETTINGS_FILE, None)
        if not isinstance(payload, dict):
            result = normalize_server_settings(DEFAULT_SETTINGS)
            apply_cpu_guard_settings(result.get("cpu_guard_enabled", True), result.get("cpu_queue_threshold_percent", WORKLOAD_CPU_HIGH_PERCENT))
            return result
        result = normalize_server_settings(payload)
        apply_cpu_guard_settings(result.get("cpu_guard_enabled", True), result.get("cpu_queue_threshold_percent", WORKLOAD_CPU_HIGH_PERCENT))
        return result


def save_server_settings(payload: dict) -> dict:
    current = load_server_settings()
    source = payload if isinstance(payload, dict) else {}
    if "cloudflare_public_hostname" in source:
        raw_hostname = clean(source.get("cloudflare_public_hostname", ""))
        if raw_hostname and not normalize_cloudflare_public_hostname(raw_hostname):
            raise RuntimeError("Cloudflare domain khong hop le. Vi du dung: qm-tech.io.vn hoac app.qm-tech.io.vn.")
        source = {**source, "cloudflare_public_hostname": normalize_cloudflare_public_hostname(raw_hostname)}
    if "cloudflare_tunnel_name" in source:
        source = {**source, "cloudflare_tunnel_name": normalize_cloudflare_tunnel_name(source.get("cloudflare_tunnel_name", ""))}
    next_payload = {
        **current,
        **source,
        "updated_at": utc_timestamp(),
    }
    if truthy(source.get("clear_hosted_client_secret", False), False):
        next_payload["hosted_client_secret_hash"] = ""
        next_payload.pop("hosted_client_secret", None)
    elif "hosted_client_secret" in source and not str(source.get("hosted_client_secret", "") or ""):
        next_payload["hosted_client_secret_hash"] = current.get("hosted_client_secret_hash", "")
        next_payload.pop("hosted_client_secret", None)
    result = normalize_server_settings(next_payload)
    apply_cpu_guard_settings(result.get("cpu_guard_enabled", True), result.get("cpu_queue_threshold_percent", WORKLOAD_CPU_HIGH_PERCENT))
    with SETTINGS_LOCK:
        SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        if str(os.environ.get("FUTURE_POSTGRES_ONLY", "") or "").strip().lower() in {"1", "true", "yes", "on"}:
            atomic_write_text(SETTINGS_FILE, json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8", sync_database=False)
        else:
            atomic_write_json(SETTINGS_FILE, result, indent=2)
    invalidate_top_response = globals().get("invalidate_vocab_leaderboard_response_cache")
    if callable(invalidate_top_response):
        invalidate_top_response()
    if "qm_city_npc" in source or "qmCityNpc" in source:
        try:
            result["qm_city_npc_mode_sync"] = schedule_shared_world_npc_mode_transition(result.get("qm_city_npc", {}))
        except Exception as exc:
            result["qm_city_npc_mode_sync"] = {"error": str(exc)}
    return result
