# Loaded by FUTURE.server_parts.02_users_auth_settings into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def normalize_motion_mode(value: object) -> str:
    mode = clean(value).lower()
    return "hover" if mode == "hover" else "always"


def normalize_space_w_voice(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    voice_value = clean(source.get("value") or source.get("voice") or source.get("id") or "")
    label = clean(source.get("label") or source.get("name") or source.get("text") or "")
    updated_at = clean(source.get("updated_at") or source.get("updatedAt") or source.get("cachedAt") or "")
    if voice_value and not updated_at:
        updated_at = utc_timestamp()
    return {
        "value": voice_value[:160],
        "label": label[:220],
        "updated_at": updated_at[:80],
    }


# Added 2026-07-30: stores the vocabulary accent per user with a monotonic timestamp so stale tabs cannot win.
def normalize_vocab_audio_preference(value: object, existing: dict | None = None) -> dict:
    source = value if isinstance(value, dict) else {}
    base = existing if isinstance(existing, dict) else {}
    raw_voice = clean(source.get("voice") or source.get("value") or source.get("key") or "")
    if raw_voice:
        voice = "sot:en-US" if "en-us" in raw_voice.lower() or raw_voice.lower() in {"us", "en-us"} else "sot:en-GB"
    else:
        voice = clean(base.get("voice")) or "sot:en-GB"
    has_saved_value = bool(raw_voice or clean(base.get("voice")))
    updated_at = clean(source.get("updated_at") or source.get("updatedAt") or base.get("updated_at") or "")
    try:
        updated_epoch = float(source.get("updated_epoch", source.get("updatedEpoch", 0)) or 0)
    except Exception:
        updated_epoch = 0.0
    if updated_epoch <= 0 and updated_at:
        updated_epoch = max(0.0, float(timestamp_to_epoch(updated_at) or 0))
    try:
        base_epoch = float(base.get("updated_epoch", 0) or timestamp_to_epoch(base.get("updated_at", "")) or 0)
    except Exception:
        base_epoch = 0.0
    if base.get("voice") and updated_epoch and base_epoch and updated_epoch < base_epoch:
        return {
            "voice": "sot:en-US" if "en-us" in clean(base.get("voice")).lower() else "sot:en-GB",
            "updated_at": clean(base.get("updated_at"))[:80],
            "updated_epoch": base_epoch,
        }
    if not has_saved_value:
        return {"voice": "sot:en-GB", "updated_at": "", "updated_epoch": 0.0}
    if not updated_at:
        updated_at = utc_timestamp()
    if updated_epoch <= 0:
        updated_epoch = max(0.0, float(timestamp_to_epoch(updated_at) or 0))
    return {"voice": voice[:40], "updated_at": updated_at[:80], "updated_epoch": updated_epoch}


# Added 2026-06-30: persists Ghost EN reading voice, accent, and playback speed per learner.
def normalize_ghost_en_voice(value: object, existing: dict | None = None) -> dict:
    source = value if isinstance(value, dict) else {}
    base = existing if isinstance(existing, dict) else {}
    voice_value = clean(
        source.get("voice")
        or source.get("value")
        or source.get("key")
        or base.get("voice")
        or base.get("value")
        or "sot:en-GB"
    )
    label = clean(source.get("label") or source.get("name") or base.get("label") or "")
    accent = clean(source.get("accent") or source.get("voice_accent") or source.get("voiceAccent") or base.get("accent") or "").lower()
    if accent not in {"uk", "us"}:
        accent = "us" if "en-us" in voice_value.lower() else "uk"
    try:
        rate = float(source.get("rate", source.get("playback_rate", source.get("playbackRate", base.get("rate", 1)))) or 1)
    except Exception:
        rate = 1.0
    rate = max(0.5, min(1.5, rate))
    updated_at = clean(source.get("updated_at") or source.get("updatedAt") or base.get("updated_at") or "")
    if not updated_at:
        updated_at = utc_timestamp()
    return {
        "voice": (voice_value or "sot:en-GB")[:180],
        "label": label[:220],
        "accent": accent,
        "rate": round(rate, 3),
        "updated_at": updated_at[:80],
    }


def normalize_chat_voice(value: object, default_voice: str = "male-us") -> dict:
    source = value if isinstance(value, dict) else {}
    fallback = clean(default_voice) or "male-us"
    voice_value = clean(source.get("voice") or source.get("value") or source.get("id") or fallback)
    label = clean(source.get("label") or source.get("name") or "")
    enabled_raw = source.get("enabled", source.get("audio_enabled", source.get("audioEnabled", False)))
    if isinstance(enabled_raw, str):
        enabled = clean(enabled_raw).lower() in {"1", "true", "yes", "on", "enabled"}
    else:
        enabled = bool(enabled_raw)
    updated_at = clean(source.get("updated_at") or source.get("updatedAt") or "")
    if not updated_at:
        updated_at = utc_timestamp()
    return {
        "voice": (voice_value or fallback)[:180],
        "label": label[:220],
        "enabled": enabled,
        "updated_at": updated_at[:80],
    }


def normalize_task_notice_style(value: object, default: str = "hologram") -> str:
    style = clean(value or default).lower().replace("_", "").replace("-", "").replace(" ", "")
    if style in {"face1", "aiface1"}:
        return "face1"
    if style in {"face", "face2", "aiface", "aiface2"}:
        return "face"
    return "hologram"


def normalize_task_notice_profile(value: object, existing: dict | None = None) -> dict:
    source = value if isinstance(value, dict) else {}
    base = existing if isinstance(existing, dict) else {}
    speaker_name = clean(source.get("speaker_name") or source.get("speakerName") or source.get("name") or base.get("speaker_name", ""))[:120]
    avatar = clean(source.get("avatar") or source.get("avatar_url") or source.get("avatarUrl") or base.get("avatar", ""))[:600]
    notice_style = normalize_task_notice_style(source.get("notice_style") or source.get("noticeStyle") or source.get("style") or base.get("notice_style", "hologram"))
    active_language = clean(source.get("active_language") or source.get("activeLanguage") or source.get("language") or base.get("active_language", "vi")).lower()
    if active_language not in {"vi", "en"}:
        active_language = "vi"
    draft_text = str(
        source.get(
            "draft_text",
            source.get("draftText", source.get("message", source.get("text", base.get("draft_text", "")))),
        )
        or ""
    )[:2200]
    draft_text_en = str(source.get("draft_text_en", source.get("draftTextEn", source.get("english", base.get("draft_text_en", "")))) or "")[:4400]
    draft_text_vi = str(source.get("draft_text_vi", source.get("draftTextVi", source.get("vietnamese", source.get("vi", base.get("draft_text_vi", ""))))) or "")[:4400]
    return {
        "speaker_name": speaker_name,
        "avatar": avatar,
        "notice_style": notice_style,
        "active_language": active_language,
        "draft_text": draft_text,
        "draft_text_en": draft_text_en,
        "draft_text_vi": draft_text_vi,
    }


def truthy(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        text = clean(value).lower()
        if not text:
            return default
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False
    return bool(value)


def normalize_question_side_cards(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    paused_raw = source.get(
        "effects_paused",
        source.get("effectsPaused", source.get("hidden", source.get("hide", source.get("off", False)))),
    )
    if isinstance(paused_raw, str):
        paused = clean(paused_raw).lower() in {"1", "true", "yes", "on", "paused", "pause", "hidden", "hide", "off"}
    else:
        paused = bool(paused_raw)
    return {"effects_paused": paused, "hidden": paused}


def normalize_question_animation(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    if "paused" in source:
        paused = truthy(source.get("paused"), False)
    elif "animation_paused" in source:
        paused = truthy(source.get("animation_paused"), False)
    elif "animationPaused" in source:
        paused = truthy(source.get("animationPaused"), False)
    elif "off" in source:
        paused = truthy(source.get("off"), False)
    elif "enabled" in source:
        paused = not truthy(source.get("enabled"), True)
    else:
        paused = False
    return {"paused": paused, "enabled": not paused}


# Added 2026-07-07: reuses normalized preferences during login/auth-me bursts.
def user_preferences_cache_signature(username: str) -> tuple[int, int]:
    path = user_file_path(username)
    try:
        stat = path.stat()
        return int(stat.st_mtime_ns), int(stat.st_size)
    except Exception:
        return 0, 0


# Added 2026-07-30: auth-me already trusts the PostgreSQL-backed RAM preference
# cache; avoid a fresh PostgreSQL read just to compute its cache signature.
def user_preferences_runtime_signature(username: str) -> tuple[int, str]:
    cache_key = normalize_username(username).lower()
    cached = USER_PREFERENCES_RAM_CACHE.get(cache_key)
    if isinstance(cached, dict) and isinstance(cached.get("preferences"), dict):
        preferences = cached["preferences"]
        return (
            max(0, int(cached.get("revision", preferences.get("_serverRevision", 0)) or 0)),
            clean(preferences.get("updated_at", "")),
        )
    row = server_database_load_user_preferences(username)
    return (
        max(0, int(row.get("server_revision", 0) or 0)) if isinstance(row, dict) else 0,
        clean(row.get("updated_at", "")) if isinstance(row, dict) else "",
    )


# Added 2026-07-07: returns an isolated preferences payload without JSON round trips.
def clone_user_preferences_payload(preferences: dict | None = None) -> dict:
    source = preferences if isinstance(preferences, dict) else {}
    return {
        "question_motion": dict(source.get("question_motion") if isinstance(source.get("question_motion"), dict) else {}),
        "question_side_cards": dict(source.get("question_side_cards") if isinstance(source.get("question_side_cards"), dict) else {}),
        "question_animation": dict(source.get("question_animation") if isinstance(source.get("question_animation"), dict) else {}),
        "space_w_voice": dict(source.get("space_w_voice") if isinstance(source.get("space_w_voice"), dict) else {}),
        "vocab_audio": dict(source.get("vocab_audio") if isinstance(source.get("vocab_audio"), dict) else {}),
        "ghost_en_voice": dict(source.get("ghost_en_voice") if isinstance(source.get("ghost_en_voice"), dict) else {}),
        "chat_voice": dict(source.get("chat_voice") if isinstance(source.get("chat_voice"), dict) else {}),
        "chat_voice_vi": dict(source.get("chat_voice_vi") if isinstance(source.get("chat_voice_vi"), dict) else {}),
        "task_notice_profile": dict(source.get("task_notice_profile") if isinstance(source.get("task_notice_profile"), dict) else {}),
        "pdf_compact_toolbar": dict(source.get("pdf_compact_toolbar") if isinstance(source.get("pdf_compact_toolbar"), dict) else {}),
        "pdf_settings": dict(source.get("pdf_settings") if isinstance(source.get("pdf_settings"), dict) else {}),
        "updated_at": clean(source.get("updated_at", "")),
        "_serverRevision": max(0, int(source.get("_serverRevision", source.get("server_revision", 0)) or 0)),
    }


# Added 2026-07-09: stores lightweight Space PDF/Picture UI settings in user preferences so optimize mode survives refresh/device changes.
def normalize_pdf_settings_preferences(payload: dict | None = None, existing: dict | None = None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    base = existing if isinstance(existing, dict) else {}

    def _one_of(value: object, allowed: set[str], fallback: str) -> str:
        text = clean(value).lower()
        return text if text in allowed else fallback

    def _num(value: object, fallback: float, low: float, high: float) -> float:
        try:
            number = float(value)
        except Exception:
            number = fallback
        return max(low, min(high, number))

    drawing_source = source.get("drawing_tool") or source.get("drawingTool") or {}
    if not isinstance(drawing_source, dict):
        drawing_source = {}
    drawing_base = base.get("drawing_tool") if isinstance(base.get("drawing_tool"), dict) else {}

    ui_source = source.get("ui") or source.get("ui_settings") or source.get("uiSettings") or {}
    if not isinstance(ui_source, dict):
        ui_source = {}
    ui_base = base.get("ui") if isinstance(base.get("ui"), dict) else {}

    return {
        "ocr_engine": _one_of(source.get("ocr_engine", source.get("ocrEngine", base.get("ocr_engine", "server"))), {"server", "browser", "browser-en"}, "server"),
        "scan_page_source": _one_of(source.get("scan_page_source", source.get("scanPageSource", base.get("scan_page_source", "sync"))), {"sync", "cache"}, "sync"),
        "drawing_tool": {
            "penColor": clean(drawing_source.get("penColor", drawing_base.get("penColor", "#ffd166")))[:40] or "#ffd166",
            "penWidth": int(_num(drawing_source.get("penWidth", drawing_base.get("penWidth", 5)), 5, 2, 28)),
            "eraserSize": int(_num(drawing_source.get("eraserSize", drawing_base.get("eraserSize", 34)), 34, 12, 96)),
            "textColor": clean(drawing_source.get("textColor", drawing_base.get("textColor", "#ffffff")))[:40] or "#ffffff",
            "textFont": clean(drawing_source.get("textFont", drawing_base.get("textFont", "Inter")))[:80] or "Inter",
            "textSize": int(_num(drawing_source.get("textSize", drawing_base.get("textSize", 28)), 28, 14, 72)),
            "textBold": truthy(drawing_source.get("textBold", drawing_base.get("textBold", False)), False),
            "textItalic": truthy(drawing_source.get("textItalic", drawing_base.get("textItalic", False)), False),
        },
        "ui": {
            "voice": clean(ui_source.get("voice", ui_base.get("voice", "")))[:160],
            "audioVoice": clean(ui_source.get("audioVoice", ui_base.get("audioVoice", "")))[:160],
            "aiNoticeVoice": clean(ui_source.get("aiNoticeVoice", ui_base.get("aiNoticeVoice", "")))[:160],
            "aiNoticeSpeakMode": _one_of(ui_source.get("aiNoticeSpeakMode", ui_base.get("aiNoticeSpeakMode", "once")), {"once", "click", "off"}, "once"),
            "speakReferenceVoice": clean(ui_source.get("speakReferenceVoice", ui_base.get("speakReferenceVoice", "")))[:160],
            "penActive": truthy(ui_source.get("penActive", ui_base.get("penActive", False)), False),
            "eraserActive": truthy(ui_source.get("eraserActive", ui_base.get("eraserActive", False)), False),
            "textActive": truthy(ui_source.get("textActive", ui_base.get("textActive", False)), False),
            "audioInsertActive": truthy(ui_source.get("audioInsertActive", ui_base.get("audioInsertActive", False)), False),
        },
    }


def read_user_preferences(username: str) -> dict:
    username = normalize_username(username)
    cache_key = username.lower()
    cached = USER_PREFERENCES_RAM_CACHE.get(cache_key)
    if isinstance(cached, dict) and cached.get("authority") == "postgresql" and isinstance(cached.get("preferences"), dict):
        return clone_user_preferences_payload(cached.get("preferences"))
    row = server_database_load_user_preferences(username)
    source = row.get("preferences") if isinstance(row, dict) and isinstance(row.get("preferences"), dict) else {}
    preferences = normalize_user_preferences(source, {}) if source else {}
    if preferences:
        preferences["updated_at"] = clean(row.get("updated_at") or source.get("updated_at"))
    revision = max(0, int(row.get("server_revision", 0) or 0)) if isinstance(row, dict) else 0
    if preferences:
        preferences["_serverRevision"] = revision
    USER_PREFERENCES_RAM_CACHE[cache_key] = {
        "authority": "postgresql",
        "revision": revision,
        "preferences": clone_user_preferences_payload(preferences),
    }
    if len(USER_PREFERENCES_RAM_CACHE) > 1200:
        for old_key in list(USER_PREFERENCES_RAM_CACHE.keys())[:200]:
            USER_PREFERENCES_RAM_CACHE.pop(old_key, None)
    return clone_user_preferences_payload(preferences)


def normalize_user_preferences(payload: dict, existing: dict | None = None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    base = existing if isinstance(existing, dict) else {}
    question_motion = None
    for key in ("question_motion", "questionMotion", "motion"):
        if key in source:
            question_motion = source.get(key)
            break
    if not isinstance(question_motion, dict):
        question_motion = base.get("question_motion") if isinstance(base.get("question_motion"), dict) else {}
    space_w_voice = None
    for key in ("space_w_voice", "spaceWVoice", "voice"):
        if key in source:
            space_w_voice = source.get(key)
            break
    if not isinstance(space_w_voice, dict):
        space_w_voice = base.get("space_w_voice") if isinstance(base.get("space_w_voice"), dict) else {}
    vocab_audio = None
    for key in ("vocab_audio", "vocabAudio", "space_v_voice", "spaceVVoice"):
        if key in source:
            vocab_audio = source.get(key)
            break
    if not isinstance(vocab_audio, dict):
        vocab_audio = base.get("vocab_audio") if isinstance(base.get("vocab_audio"), dict) else {}
    ghost_en_voice = None
    for key in ("ghost_en_voice", "ghostEnVoice", "ghost_en"):
        if key in source:
            ghost_en_voice = source.get(key)
            break
    if not isinstance(ghost_en_voice, dict):
        ghost_en_voice = base.get("ghost_en_voice") if isinstance(base.get("ghost_en_voice"), dict) else {}
    chat_voice = None
    for key in ("chat_voice", "chatVoice"):
        if key in source:
            chat_voice = source.get(key)
            break
    if not isinstance(chat_voice, dict):
        chat_voice = base.get("chat_voice") if isinstance(base.get("chat_voice"), dict) else {}
    chat_voice_vi = None
    for key in ("chat_voice_vi", "chatVoiceVi", "chatVoiceVI"):
        if key in source:
            chat_voice_vi = source.get(key)
            break
    if not isinstance(chat_voice_vi, dict):
        chat_voice_vi = base.get("chat_voice_vi") if isinstance(base.get("chat_voice_vi"), dict) else {}
    question_side_cards = None
    for key in ("question_side_cards", "questionSideCards"):
        if key in source:
            question_side_cards = source.get(key)
            break
    if not isinstance(question_side_cards, dict):
        question_side_cards = base.get("question_side_cards") if isinstance(base.get("question_side_cards"), dict) else {}
    question_animation = None
    for key in ("question_animation", "questionAnimation"):
        if key in source:
            question_animation = source.get(key)
            break
    if not isinstance(question_animation, dict):
        question_animation = base.get("question_animation") if isinstance(base.get("question_animation"), dict) else {}
    task_notice_profile = None
    for key in ("task_notice_profile", "taskNoticeProfile"):
        if key in source:
            task_notice_profile = source.get(key)
            break
    if not isinstance(task_notice_profile, dict):
        task_notice_profile = base.get("task_notice_profile") if isinstance(base.get("task_notice_profile"), dict) else {}
    pdf_compact_toolbar = None
    for key in ("pdf_compact_toolbar", "pdfCompactToolbar", "pdf_compact", "pdfCompact"):
        if key in source:
            pdf_compact_toolbar = source.get(key)
            break
    if not isinstance(pdf_compact_toolbar, dict):
        pdf_compact_toolbar = base.get("pdf_compact_toolbar") if isinstance(base.get("pdf_compact_toolbar"), dict) else {}
    pdf_settings = None
    for key in ("pdf_settings", "pdfSettings", "pdf"):
        if key in source:
            pdf_settings = source.get(key)
            break
    if not isinstance(pdf_settings, dict):
        pdf_settings = base.get("pdf_settings") if isinstance(base.get("pdf_settings"), dict) else {}
    return {
        "question_motion": {
            "picture": normalize_motion_mode(question_motion.get("picture", "always")),
            "audio": normalize_motion_mode(question_motion.get("audio", "always")),
        },
        "question_side_cards": normalize_question_side_cards(question_side_cards),
        "question_animation": normalize_question_animation(question_animation),
        "space_w_voice": normalize_space_w_voice(space_w_voice),
        "vocab_audio": normalize_vocab_audio_preference(vocab_audio, base.get("vocab_audio") if isinstance(base.get("vocab_audio"), dict) else {}),
        "ghost_en_voice": normalize_ghost_en_voice(
            ghost_en_voice,
            base.get("ghost_en_voice") if isinstance(base.get("ghost_en_voice"), dict) else {},
        ),
        "chat_voice": normalize_chat_voice(chat_voice),
        "chat_voice_vi": normalize_chat_voice(chat_voice_vi, "edge:vi-VN-NamMinhNeural"),
        "task_notice_profile": normalize_task_notice_profile(
            task_notice_profile,
            base.get("task_notice_profile") if isinstance(base.get("task_notice_profile"), dict) else {},
        ),
        "pdf_compact_toolbar": {
            "enabled": True,
        },
        "pdf_settings": normalize_pdf_settings_preferences(
            pdf_settings,
            base.get("pdf_settings") if isinstance(base.get("pdf_settings"), dict) else {},
        ),
        "updated_at": utc_timestamp(),
    }


def save_user_preferences(username: str, preferences_payload: dict) -> dict:
    username = normalize_username(username)
    current = read_user_preferences(username)
    candidate = normalize_user_preferences(preferences_payload, current)
    if server_database_preference_identity(candidate) == server_database_preference_identity(current):
        return clone_user_preferences_payload(current)
    result = server_database_save_user_preferences(username, preferences_payload)
    preferences = result.get("preferences") if isinstance(result, dict) and isinstance(result.get("preferences"), dict) else candidate
    revision = max(1, int(result.get("server_revision", 1) or 1)) if isinstance(result, dict) else 1
    preferences["_serverRevision"] = revision
    cache_key = username.lower()
    cached = USER_PREFERENCES_RAM_CACHE.get(cache_key)
    cached_revision = max(0, int(cached.get("revision", 0) or 0)) if isinstance(cached, dict) else 0
    if revision >= cached_revision:
        USER_PREFERENCES_RAM_CACHE[cache_key] = {
            "authority": "postgresql",
            "revision": revision,
            "preferences": clone_user_preferences_payload(preferences),
        }
    response = clone_user_preferences_payload(preferences)
    if isinstance(result, dict) and result.get("conflict"):
        response["_preferenceConflict"] = True
    return response
