# Loaded by FUTURE.server_parts.04_ai_language_agents into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def chat_builder_tools():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(PROGRAME_ROOT) not in sys.path:
        sys.path.insert(0, str(PROGRAME_ROOT))
    import future_lesson_builder_gui as builder  # type: ignore
    # Added 2026-08-01: keep TTS asset writes on the active Server 2 data root (including isolated test roots), never the builder's import-time default.
    active_root = Path(
        os.environ.get("FUTURE_SERVER_DATA_ROOT", "")
        or globals().get("SERVER_DATA_ROOT", "")
        or getattr(builder, "SERVER_DATA_ROOT", r"C:\server data")
    ).resolve()
    builder.SERVER_DATA_ROOT = active_root
    builder.SERVER_SOUND_DIR = active_root / "Sound"
    builder.SERVER_STRUCTURE_DIR = active_root / "Structure"
    builder.SERVER_PICTURE_DIR = active_root / "Picture"
    try:
        asset_globals = builder.indexed_write_server_sound_asset.__globals__
        configure_root = asset_globals.get("configure_sound_asset_root")
        if callable(configure_root):
            configure_root(active_root)
        else:
            asset_globals["SERVER_DATA_ROOT"] = active_root
            asset_globals["SERVER_SOUND_DIR"] = active_root / "Sound"
            asset_globals["SERVER_SOUND_V2_DIR"] = active_root / "Sound" / "_v2"
            asset_globals["SOUND_ASSET_INDEX_FILE"] = active_root / "_future_sound_asset_index.json"
            asset_globals["SOUND_ASSET_INDEX_WAL_FILE"] = active_root / "_future_sound_asset_index.wal.jsonl"
    except (AttributeError, KeyError):
        pass
    return builder


# Added 2026-08-01: verifies one completed Sound write and repairs only its exact index entry before callers persist audioPath.
def chat_finalize_sound_audio_payload(payload: dict | None) -> dict:
    result = dict(payload) if isinstance(payload, dict) else {}
    audio_path = clean(result.get("audio_path", result.get("audioPath", "")))
    if not audio_path.lower().startswith("sound/"):
        return result
    builder = chat_builder_tools()
    asset_globals = builder.indexed_write_server_sound_asset.__globals__
    ensure_entry = asset_globals.get("ensure_sound_asset_index_entry")
    if not callable(ensure_entry):
        raise RuntimeError("Sound index helper is unavailable.")
    index_result = ensure_entry(audio_path)
    if not isinstance(index_result, dict) or not index_result.get("ok"):
        raise RuntimeError(f"Sound file/index is not ready: {audio_path}")
    result["sound_index_key"] = clean(index_result.get("key", ""))
    result["sound_index_repaired"] = bool(index_result.get("index_repaired"))
    return result


VIETNAMESE_MARK_RE = re.compile(r"[ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", re.I)


def translation_compare_key(value: str) -> str:
    return re.sub(r"[\W_]+", "", str(value or "").lower(), flags=re.UNICODE)


def translation_result_is_usable(source: str, translated: str, dest: str = "en") -> bool:
    output = str(translated or "").strip()
    if not output:
        return False
    source_key = translation_compare_key(source)
    output_key = translation_compare_key(output)
    if source_key and output_key and source_key == output_key:
        return False
    target = clean(dest).lower()
    if target == "en" and VIETNAMESE_MARK_RE.search(output):
        return False
    return True


# Added 2026-06-30: keeps shared translator retries from failing on a single slow/bad source guess.
def chat_translate_source_attempts(src: str) -> list[str]:
    first_src = clean(src).lower() or "auto"
    attempts = [first_src]
    if first_src != "auto":
        attempts.append("auto")
    return list(dict.fromkeys(attempts))


def chat_translate_text(text: str, dest: str = "en", src: str = "auto", limit: int = 2200, max_wait_seconds: int | float = 0, preferred_user: str = "", force_refresh: bool = False) -> str:
    source = str(text or "").strip()
    if not source:
        return ""
    try:
        from FUTURE.server_parts.worker_jobs.heavy_language_jobs import translate_text_once_worker
        target = clean(dest).lower() or "auto"
        attempts = chat_translate_source_attempts(src)
        last_error = ""
        wait_seconds = max(0.0, float(max_wait_seconds or 0) or 0.0)
        deadline = time.monotonic() + wait_seconds if wait_seconds > 0 else 0.0
        retry_index = 0
        deadline_expired = False
        while True:
            retry_index += 1
            for attempt_src in attempts:
                attempt_timeout = 0
                if deadline > 0:
                    remaining_for_attempt = deadline - time.monotonic()
                    if remaining_for_attempt <= 0:
                        deadline_expired = True
                        break
                    attempt_timeout = max(1, int(remaining_for_attempt + 0.999))
                try:
                    result = distributed_worker_try_translate(
                        source,
                        dest=dest,
                        src=attempt_src,
                        limit=max(1, int(limit or 2200)),
                        timeout_seconds=attempt_timeout or 8,
                        preferred_user=preferred_user,
                        force_refresh=force_refresh,
                    )
                    if not result:
                        result = TRANSLATE_WORK_QUEUE.run(
                            f"{attempt_src}->{target}:retry-{retry_index}",
                            translate_text_once_worker,
                            source,
                            dest,
                            attempt_src,
                            max(1, int(limit or 2200)),
                            force_refresh,
                            timeout=attempt_timeout,
                        )
                except Exception as exc:
                    last_error = str(exc)
                    if deadline > 0 and time.monotonic() >= deadline:
                        deadline_expired = True
                        break
                    continue
                translated = lesson_task_notice_text(result or "", limit=max(1, int(limit or 2200)))
                if translation_result_is_usable(source, translated, dest):
                    return translated
                last_error = "Ket qua dich khong dung ngon ngu dich."
            if deadline_expired:
                break
            if deadline > 0:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                delay = min(2.5, max(0.45, 0.45 * float(retry_index)))
                time.sleep(max(0.05, min(remaining, delay)))
                continue
            if retry_index >= 3:
                break
            time.sleep(0.45 * float(retry_index))
        raise RuntimeError(last_error or "Ket qua dich khong dung ngon ngu dich.")
    except Exception as exc:
        raise RuntimeError(f"Khong dich duoc van ban: {exc}")


def chat_translate_to_english(text: str) -> str:
    try:
        return chat_translate_text(text, dest="en", src="vi")
    except Exception as exc:
        raise RuntimeError(f"Khong dich duoc sang tieng Anh: {exc}")


def task_notice_translate_to_vietnamese(text: str) -> str:
    try:
        return chat_translate_text(text, dest="vi", src="en", limit=9000)
    except Exception:
        return ""


def task_notice_translate_to_english(text: str) -> str:
    try:
        return chat_translate_text(text, dest="en", src="vi", limit=9000)
    except Exception:
        return ""


def chat_voice_option_payload(force_refresh: bool = False) -> dict:
    if SERVER_STATE.get("loading") and not SERVER_STATE.get("ready"):
        return {
            "vi": [
                {"label": "Edge | Vietnamese VN | Nam Minh", "key": "edge:vi-VN-NamMinhNeural"},
                {"label": "Edge | Vietnamese VN | Hoai My", "key": "edge:vi-VN-HoaiMyNeural"},
                {"label": "Kokoro VI | Diem Trinh", "key": "kokoro_vi:diem_trinh"},
                {"label": "Kokoro VI | Hung Thinh", "key": "kokoro_vi:hung_thinh"},
                {"label": "Kokoro VI | Mai Linh", "key": "kokoro_vi:mai_linh"},
            ],
            "en": [
                {"label": "People | Male Michael", "key": "kokoro:am_michael"},
                {"label": "People | Male Adam", "key": "kokoro:am_adam"},
            ],
            "ready": False,
            "error": "Voice catalog waits until Whisper is ready.",
        }
    with CHAT_VOICE_LOCK:
        if CHAT_VOICE_OPTIONS.get("ready") and not force_refresh:
            return dict(CHAT_VOICE_OPTIONS)
    try:
        builder = chat_builder_tools()
        vi_source = list(builder.edge_vietnamese_voice_specs(force_refresh=force_refresh) or []) + list(builder.kokoro_vietnamese_voice_specs() or [])
        vi_priority = ["edge:vi-VN-NamMinhNeural", "edge:vi-VN-HoaiMyNeural", "kokoro_vi:diem_trinh", "kokoro_vi:hung_thinh", "kokoro_vi:mai_linh"]
        vi_map = {clean(key).lower(): (clean(label), clean(key)) for label, key in vi_source}
        vi_options = []
        seen = set()
        for key in vi_priority:
            lowered = key.lower()
            label, value = vi_map.get(lowered, ("", key))
            if lowered not in seen:
                seen.add(lowered)
                vi_options.append({"label": label or builder.embedded_voice_label(value), "key": value})
        for label, key in vi_source:
            lowered = clean(key).lower()
            if lowered.startswith(("edge:", "kokoro_vi:")) and lowered not in seen:
                seen.add(lowered)
                vi_options.append({"label": clean(label) or builder.embedded_voice_label(key), "key": clean(key)})

        en_options = []
        seen = set()
        for label, key in list(builder.people_voice_specs() or []) + list(builder.microsoft_voice_specs(force_refresh=force_refresh) or []):
            clean_key = clean(key)
            lowered = clean_key.lower()
            if not clean_key or lowered in seen:
                continue
            seen.add(lowered)
            en_options.append({"label": clean(label) or builder.embedded_voice_label(clean_key), "key": clean_key})
        payload = {"vi": vi_options, "en": en_options, "ready": True, "error": ""}
    except Exception as exc:
        payload = {
            "vi": [
                {"label": "Edge | Vietnamese VN | Nam Minh", "key": "edge:vi-VN-NamMinhNeural"},
                {"label": "Edge | Vietnamese VN | Hoai My", "key": "edge:vi-VN-HoaiMyNeural"},
                {"label": "Kokoro VI | Diem Trinh", "key": "kokoro_vi:diem_trinh"},
                {"label": "Kokoro VI | Hung Thinh", "key": "kokoro_vi:hung_thinh"},
                {"label": "Kokoro VI | Mai Linh", "key": "kokoro_vi:mai_linh"},
            ],
            "en": [
                {"label": "People | Male Michael", "key": "kokoro:am_michael"},
                {"label": "People | Male Adam", "key": "kokoro:am_adam"},
            ],
            "ready": False,
            "error": str(exc),
        }
    with CHAT_VOICE_LOCK:
        CHAT_VOICE_OPTIONS.clear()
        CHAT_VOICE_OPTIONS.update(payload)
        return dict(CHAT_VOICE_OPTIONS)


# Added 2026-06-30: returns Space_P-style audio-guided timing rows for generated chat/PDF voices.
def chat_audio_timing_payload(builder, source: str, voice: str, audio_bytes: bytes, mime: str) -> dict:
    analyzed = builder.analyze_sentence(source)
    tokens = builder.sentence_spans(source, analyzed, voice)
    duration_ms = builder.audio_duration_ms(audio_bytes, mime)
    if duration_ms <= 0:
        duration_ms = builder.estimate_duration_ms(source, tokens)
    timings = builder.build_audio_guided_timings(tokens, duration_ms, audio_bytes) or builder.build_timings(tokens, duration_ms)
    timing_tokens = []
    for index, token in enumerate(tokens):
        row = {
            "t": clean(token.get("t") or token.get("text")),
            "s": int(token.get("s", index) or index),
            "e": int(token.get("e", index + 1) or (index + 1)),
        }
        ipa = clean(token.get("i") or token.get("ipa"))
        if ipa:
            row["i"] = ipa
        timing_tokens.append(row)
    payload = {}
    if duration_ms > 0:
        payload["duration_ms"] = int(duration_ms)
        payload["durationMs"] = int(duration_ms)
    if timing_tokens:
        payload["timing_tokens"] = timing_tokens
        payload["timingTokens"] = timing_tokens
    if timings:
        payload["timings"] = timings
    return payload


def chat_synthesize_message_audio(text: str, voice_key: str) -> dict:
    source = str(text or "").strip()
    voice = clean(voice_key)
    if not source:
        raise RuntimeError("Tin nhan dang trong.")
    if not voice:
        raise RuntimeError("Chua chon voice.")
    builder = chat_builder_tools()
    audio_bytes, mime = builder.synthesize_embedded_audio(source, voice, lambda message: stt_debug_log("chat_tts", message=message))
    voice_label = builder.embedded_voice_label(voice)
    audio_path = builder.write_server_sound_asset(f"chat-{voice}-{source[:36]}", audio_bytes, mime)
    timing_payload = chat_audio_timing_payload(builder, source, voice, audio_bytes, mime)
    audio_payload = {
        "path": audio_path,
        "mime": mime,
        "voice": builder.normalize_audio_voice_key(voice) or voice,
        "label": voice_label,
    }
    audio_payload.update(timing_payload)
    return chat_finalize_sound_audio_payload({
        "audio_path": audio_path,
        "audio_mime": mime,
        "voice": builder.normalize_audio_voice_key(voice) or voice,
        "voice_label": voice_label,
        **timing_payload,
        "audio": audio_payload,
    })


# Added 2026-07-07: stores audio bytes returned by a distributed TTS worker on the server Sound path.
def chat_remote_tts_payload(text: str, voice_key: str, raw: dict) -> dict:
    source = str(text or "").strip()
    voice = clean(voice_key)
    builder = chat_builder_tools()
    audio_bytes = raw.get("audio_bytes") or b""
    if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
        raise RuntimeError("Distributed worker did not return audio bytes.")
    mime = clean(raw.get("audio_mime", "")) or clean(raw.get("mime", "")) or "audio/mpeg"
    normalized_voice = builder.normalize_audio_voice_key(clean(raw.get("voice", "")) or voice) or voice
    voice_label = clean(raw.get("voice_label", "")) or builder.embedded_voice_label(voice)
    audio_path = builder.write_server_sound_asset(f"chat-{normalized_voice}-{source[:36]}", bytes(audio_bytes), mime)
    timing_payload = {}
    for key in ("duration_ms", "durationMs", "timing_tokens", "timingTokens", "timings"):
        if key in raw:
            timing_payload[key] = raw[key]
    audio_payload = {
        "path": audio_path,
        "mime": mime,
        "voice": normalized_voice,
        "label": voice_label,
    }
    audio_payload.update(timing_payload)
    return chat_finalize_sound_audio_payload({
        "audio_path": audio_path,
        "audio_mime": mime,
        "voice": normalized_voice,
        "voice_label": voice_label,
        **timing_payload,
        "audio": audio_payload,
        "remote_worker": True,
    })


def chat_synthesize_message_audio_queued(
    text: str,
    voice_key: str,
    preferred_user: str = "",
    source: str = "runtime_voice",
) -> dict:
    normalized_voice = clean(voice_key)
    requires_remote_kokoro_vi = normalized_voice.lower().startswith("kokoro_vi:")
    try:
        raw = durable_tts_submit_raw(
            text,
            normalized_voice,
            priority=1,
            source=source,
            timeout_seconds=VOICE_WORK_QUEUE.timeout_seconds,
            preferred_user=preferred_user,
            params={"timeout_seconds": 0 if normalized_voice.lower().startswith("kokoro_vi:") else VOICE_WORK_QUEUE.timeout_seconds},
        )
        if raw:
            return chat_finalize_sound_audio_payload(chat_remote_tts_payload(text, normalized_voice, raw))
    except Exception as exc:
        stt_debug_log("distributed_tts_fallback", voice=normalized_voice, error=str(exc))
    if requires_remote_kokoro_vi and clean(os.environ.get("FUTURE_KOKORO_VI_SERVER_FALLBACK", "")).lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("Kokoro VI voice needs an online worker with Python 3.11 + kokoro-vietnamese/onnxruntime/soundfile. Server 2 fallback is disabled to avoid heavy CPU/RAM.")
    if VOICE_WORKER_ENABLED:
        try:
            return chat_finalize_sound_audio_payload(synthesize_message_audio_via_voice_worker(text, normalized_voice, timeout=VOICE_WORK_QUEUE.timeout_seconds))
        except Exception as exc:
            stt_debug_log("voice_worker_fallback", voice=normalized_voice, error=str(exc))
    try:
        from FUTURE.server_parts.worker_jobs.heavy_language_jobs import synthesize_message_audio_worker
        return chat_finalize_sound_audio_payload(VOICE_WORK_QUEUE.run(
            f"voice:{normalized_voice[:40]}",
            synthesize_message_audio_worker,
            text,
            normalized_voice,
            timeout=VOICE_WORK_QUEUE.timeout_seconds,
        ))
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError("Queue tao voice dang qua tai, hay thu lai sau.") from exc


# Added 2026-07-02: routes admin MishiKa AI Question audio builds away from user-facing Ghost AI voice work.
def chat_synthesize_ai_question_audio_queued(text: str, voice_key: str, preferred_user: str = "") -> dict:
    try:
        raw = durable_tts_submit_raw(
            text,
            voice_key,
            priority=1,
            source="admin_ai_question",
            timeout_seconds=AI_QUESTION_VOICE_WORK_QUEUE.timeout_seconds,
            preferred_user=preferred_user,
            params={"timeout_seconds": AI_QUESTION_VOICE_WORK_QUEUE.timeout_seconds},
        )
        if raw:
            return chat_finalize_sound_audio_payload(chat_remote_tts_payload(text, voice_key, raw))
    except Exception as exc:
        stt_debug_log("distributed_tts_ai_question_fallback", voice=clean(voice_key), error=str(exc))
    if VOICE_WORKER_ENABLED:
        try:
            return chat_finalize_sound_audio_payload(synthesize_message_audio_via_voice_worker(text, voice_key, timeout=AI_QUESTION_VOICE_WORK_QUEUE.timeout_seconds))
        except Exception as exc:
            stt_debug_log("voice_worker_ai_question_fallback", voice=clean(voice_key), error=str(exc))
    try:
        from FUTURE.server_parts.worker_jobs.heavy_language_jobs import synthesize_message_audio_worker
        return chat_finalize_sound_audio_payload(AI_QUESTION_VOICE_WORK_QUEUE.run(
            f"ai-question:{clean(voice_key)[:40]}",
            synthesize_message_audio_worker,
            text,
            voice_key,
            timeout=AI_QUESTION_VOICE_WORK_QUEUE.timeout_seconds,
        ))
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError("Queue tao voice AI Question dang qua tai, hay thu lai sau.") from exc


def warm_chat_voice_modules_async() -> None:
    def worker() -> None:
        try:
            payload = chat_voice_option_payload(force_refresh=False)
            # Do not synthesize audio during server boot. Edge/Kokoro native work can
            # collide with faster-whisper preload on Windows and crash the process.
            stt_debug_log("chat_voice_catalog_warm_done", vi=len(payload.get("vi", []) or []), en=len(payload.get("en", []) or []))
        except Exception as exc:
            stt_debug_log("chat_voice_warm_error", error=str(exc), traceback=traceback.format_exc())

    threading.Thread(target=worker, name="future-chat-voice-warm", daemon=True).start()
