# Loaded by FUTURE.server_parts.07_server_data_pdf_qmdict into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def ensure_space_v_audio_builder_import_deps() -> None:
    """Expose bundled pure-Python packages needed when importing builder GUI helpers."""
    try:
        import openpyxl  # noqa: F401, PLC0415
        return
    except Exception:
        pass
    try:
        import sys  # noqa: PLC0415
        from pathlib import Path  # noqa: PLC0415

        site_packages = (
            Path.home()
            / ".cache"
            / "codex-runtimes"
            / "codex-primary-runtime"
            / "dependencies"
            / "python"
            / "Lib"
            / "site-packages"
        )
        if site_packages.is_dir():
            site_text = str(site_packages)
            if site_text not in sys.path:
                sys.path.append(site_text)
    except Exception:
        pass

def qmdict_space_v_meaning_audio_map(meaning: object = "", *, online_fallback: bool = True) -> dict:
    text = clean(meaning)
    if not text:
        return {}
    try:
        from future_vocab_builder_gui import DEFAULT_MEANING_VOICE, vocab_audio_clip  # noqa: PLC0415

        _label, voice_key, short_key = DEFAULT_MEANING_VOICE
        clip = vocab_audio_clip(text, voice_key, lambda message: stt_debug_log("space_v_qmdict_audio", message=message), online_fallback=online_fallback)
        return {voice_key: clip, short_key: clip} if clip else {}
    except Exception as exc:
        stt_debug_log("space_v_qmdict_audio_sot_failed", error=str(exc))
    if not online_fallback:
        return {}
    try:
        audio_payload = chat_synthesize_message_audio_queued(text, "edge:vi-VN-NamMinhNeural")
        clip = audio_payload.get("audio") if isinstance(audio_payload.get("audio"), dict) else {}
        if clip and clean(clip.get("path", "")) and not clean(clip.get("u", "")):
            clip = {"u": clean(clip.get("path", "")), "m": clean(clip.get("mime", "audio/mpeg")) or "audio/mpeg", "voice": clean(clip.get("voice", ""))}
        if not clip and clean(audio_payload.get("audio_path", "")):
            clip = {"u": clean(audio_payload.get("audio_path", "")), "m": clean(audio_payload.get("audio_mime", "audio/mpeg")) or "audio/mpeg"}
        return {"edge:vi-VN-NamMinhNeural": clip, "vi": clip} if clip else {}
    except Exception as exc:
        stt_debug_log("space_v_qmdict_audio_fallback_failed", error=str(exc))
    return {}


def qmdict_audio_refresh_job_snapshot() -> dict:
    with QMDICT_AUDIO_REFRESH_LOCK:
        return dict(QMDICT_AUDIO_REFRESH_JOB)


def qmdict_word_audio_refresh_job_snapshot() -> dict:
    with QMDICT_WORD_AUDIO_REFRESH_LOCK:
        return dict(QMDICT_WORD_AUDIO_REFRESH_JOB)


def write_qmdict_audio_refresh_progress(payload: dict) -> None:
    try:
        atomic_write_json(QMDICT_AUDIO_REFRESH_PROGRESS_FILE, payload, indent=2)
    except Exception as exc:
        stt_debug_log("qmdict_audio_refresh_progress_failed", error=str(exc))


def write_qmdict_word_audio_refresh_progress(payload: dict) -> None:
    try:
        atomic_write_json(QMDICT_WORD_AUDIO_REFRESH_PROGRESS_FILE, payload, indent=2)
    except Exception as exc:
        stt_debug_log("qmdict_word_audio_refresh_progress_failed", error=str(exc))


def normalize_qmlearn_audio_voice_key(voice_key: object = "") -> str:
    text = clean(voice_key) or "sot:en-GB"
    if text.lower().startswith("sot:"):
        text = text[4:]
    aliases = {
        "en-UK": "en-GB",
        "en_UK": "en-GB",
        "en_US": "en-US",
        "vi_VN": "vi-VN",
    }
    return aliases.get(text, text)


def qmlearn_audio_lang_candidates(voice_key: object = "") -> list[str]:
    voice = normalize_qmlearn_audio_voice_key(voice_key)
    out: list[str] = []

    def add(value: str) -> None:
        value = clean(value)
        if value and value not in out:
            out.append(value)

    add(voice)
    lower = voice.lower()
    if lower == "vi-vn":
        add("vi")
    elif lower == "vi":
        add("vi-VN")
    elif lower.startswith("en-"):
        add("en")
    elif lower == "en":
        add("en-GB")
        add("en-US")
    return out


def qmlearn_audio_voice_dir(voice_key: object = "") -> Path:
    raw = clean(voice_key) or "sot:en-GB"
    if raw.lower().startswith("sot:"):
        base = f"sot:{normalize_qmlearn_audio_voice_key(raw)}"
    else:
        base = raw
    folder = base.lower().replace(":", "-").replace("/", "-").replace("\\", "-")
    folder = re.sub(r"\s+", "-", folder)
    folder = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "-", folder)
    folder = re.sub(r"-{2,}", "-", folder).strip("-.")
    return QMLEARN_DATA_ROOT / folder if folder else QMLEARN_DATA_ROOT


def synthesize_space_v_sound_of_text_bytes(text: object = "", voice_key: object = "", log=None) -> bytes:
    target_text = clean(text)
    target_voice = normalize_qmlearn_audio_voice_key(voice_key) or "en-GB"
    if not target_text:
        raise RuntimeError("Thieu tu vung can tao audio.")
    try:
        if callable(log):
            log(f"Sound of Text direct: {target_text} ({target_voice})")
        from module_main.Soundoftext_Api import Soundoftext_Api  # noqa: PLC0415

        audio_bytes = Soundoftext_Api().load_mp3_bytes(target_text, voice=target_voice)
        if audio_bytes:
            return bytes(audio_bytes)
        raise RuntimeError(f"Sound of Text khong tra audio cho {target_voice}.")
    except Exception as first_exc:
        if callable(log):
            log(f"Sound of Text direct failed: {first_exc}")
        try:
            from future_lesson_builder_gui import synthesize_embedded_audio  # noqa: PLC0415

            audio_bytes, _mime = synthesize_embedded_audio(target_text, f"sot:{target_voice}", log)
            if audio_bytes:
                return bytes(audio_bytes)
        except Exception as second_exc:
            raise RuntimeError(f"{first_exc}; fallback: {second_exc}") from second_exc
        raise

def force_save_space_v_sound_audio(text: object = "", voice_key: object = "", audio_bytes: bytes | None = None, log=None) -> Path | None:
    target_text = clean(text)
    target_voice = normalize_qmlearn_audio_voice_key(voice_key) or "en-GB"
    if not target_text or not audio_bytes:
        return None
    try:
        from module_main.Data_Input.local_sound_loader import clear_internal_cache, save_sound_bytes  # noqa: PLC0415
    except Exception as exc:
        if callable(log):
            log(f"Skip QMLearn/Data save {target_text}: {exc}")
        return None
    voice_dir = qmlearn_audio_voice_dir(f"sot:{target_voice}")
    voice_dir.mkdir(parents=True, exist_ok=True)
    try:
        saved_path = clean(save_sound_bytes(target_text, target_voice, bytes(audio_bytes), data_dir=str(voice_dir), overwrite=True))
        clear_internal_cache()
    except Exception as exc:
        if callable(log):
            log(f"Skip QMLearn/Data save {target_text}: {exc}")
        return None
    if not saved_path:
        return None
    candidate = Path(saved_path)
    try:
        candidate = candidate.resolve()
        candidate.relative_to(QMLEARN_DATA_ROOT.resolve())
    except Exception:
        return None
    if candidate.is_file():
        if callable(log):
            log(f"QMLearn/Data forced save: {target_text} (sot:{target_voice})")
        return candidate
    return None

QMLEARN_SOUND_EXTENSIONS = (".mp3", ".txt")
QMLEARN_INVALID_FILENAME_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]')


def qmlearn_display_sound_lang(lang: object = "") -> str:
    text = clean(lang).strip().lower().replace("_", "-")
    if not text:
        return ""
    if "-" in text:
        left, right = text.split("-", 1)
        return f"{left.lower()}-{right.upper()}"
    return text.lower()


def qmlearn_normalize_sound_variant(value: object = "") -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    if not text:
        return ""
    text = text.replace(":", "-").replace("/", "-").replace("\\", "-")
    text = re.sub(r"\s+", "-", text)
    text = QMLEARN_INVALID_FILENAME_CHARS_RE.sub("-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-.")


def qmlearn_build_sound_storage_stem(word: object = "") -> str:
    text = unicodedata.normalize("NFKC", str(word or "")).strip()
    if not text:
        return ""
    text = text.replace("/", " ").replace("\\", " ")
    text = text.replace(":", " ").replace("*", " ")
    text = text.replace("?", " ").replace('"', " ")
    text = text.replace("<", " ").replace(">", " ").replace("|", " ")
    text = re.sub(r"\s+", " ", text).strip().strip(".")
    text = QMLEARN_INVALID_FILENAME_CHARS_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip().strip(".")
    return text[:180].strip()


def qmlearn_build_sound_file_name(word: object = "", lang: object = "", variant: object = "", extension: object = ".mp3") -> str:
    stem = qmlearn_build_sound_storage_stem(word)
    lang_text = qmlearn_display_sound_lang(lang)
    if not stem or not lang_text:
        return ""
    ext = clean(extension).lower() or ".mp3"
    if ext not in QMLEARN_SOUND_EXTENSIONS:
        ext = ".mp3"
    variant_text = qmlearn_normalize_sound_variant(variant)
    if variant_text:
        return f"{stem}_{lang_text}__{variant_text}{ext}"
    return f"{stem}_{lang_text}{ext}"


def qmlearn_audio_build_helpers() -> tuple[object | None, object | None]:
    with QMLEARN_AUDIO_HELPERS_LOCK:
        if QMLEARN_AUDIO_HELPERS.get("loaded"):
            return QMLEARN_AUDIO_HELPERS.get("file_name"), QMLEARN_AUDIO_HELPERS.get("stem")
    file_name_builder = qmlearn_build_sound_file_name
    stem_builder = qmlearn_build_sound_storage_stem
    with QMLEARN_AUDIO_HELPERS_LOCK:
        QMLEARN_AUDIO_HELPERS["loaded"] = True
        QMLEARN_AUDIO_HELPERS["file_name"] = file_name_builder
        QMLEARN_AUDIO_HELPERS["stem"] = stem_builder
    return file_name_builder, stem_builder


def qmlearn_audio_dir_index(root: Path) -> dict[str, Path]:
    try:
        root_path = Path(root).resolve()
        root_path.relative_to(QMLEARN_DATA_ROOT.resolve())
    except Exception:
        return {}
    key = str(root_path).lower()
    with QMLEARN_AUDIO_DIR_INDEX_LOCK:
        cached = QMLEARN_AUDIO_DIR_INDEX.get(key)
        if cached is not None:
            return cached
    index: dict[str, Path] = {}
    try:
        if root_path.is_dir():
            for child in root_path.iterdir():
                try:
                    if child.is_file() and child.suffix.lower() in {".mp3", ".txt"}:
                        index.setdefault(child.name.lower(), child)
                except Exception:
                    continue
    except Exception:
        index = {}
    with QMLEARN_AUDIO_DIR_INDEX_LOCK:
        QMLEARN_AUDIO_DIR_INDEX[key] = index
    return index


# Added 2026-07-14: warms UK/US QMLearn audio filename indexes without loading audio bytes into RAM.
def warm_qmlearn_voice_audio_index_async(delay_seconds: float = 0.0) -> None:
    # Added 2026-07-21: load the persisted root stem set before warm-ready so first lessons never scan the huge flat audio folder.
    root_stems = qmdict_audio_stem_index_shared()

    def _worker() -> None:
        try:
            if delay_seconds and delay_seconds > 0:
                time.sleep(min(10.0, max(0.0, float(delay_seconds or 0.0))))
            started = time.perf_counter()
            warmed: dict[str, int] = {}
            for voice in ("sot:en-GB", "sot:en-US"):
                voice_dir = qmlearn_audio_voice_dir(voice)
                index = qmlearn_audio_dir_index(voice_dir)
                warmed[voice] = len(index)
            SERVER_STATE["qmlearn_voice_index_ready"] = True
            SERVER_STATE["qmlearn_voice_index_warmed"] = warmed
            SERVER_STATE["qmlearn_root_audio_stems"] = len(root_stems)
            SERVER_STATE["qmlearn_voice_index_ms"] = int((time.perf_counter() - started) * 1000)
            stt_debug_log("qmlearn_voice_audio_index_warm_done", **warmed, elapsed_ms=SERVER_STATE["qmlearn_voice_index_ms"])
        except Exception as exc:
            SERVER_STATE["qmlearn_voice_index_ready"] = False
            SERVER_STATE["qmlearn_voice_index_error"] = str(exc)
            stt_debug_log("qmlearn_voice_audio_index_warm_failed", error=str(exc))

    threading.Thread(target=_worker, daemon=True, name="qmlearn-voice-audio-index-warm").start()


def qmlearn_cached_word_audio_payload(text: object = "", voice_key: object = "") -> dict:
    target_text = clean(text)
    target_voice = clean(voice_key)
    if not target_text or not target_voice:
        return {}
    if target_voice.lower() not in {"sot:en-gb", "sot:en-us"}:
        return {}
    audio_path = fast_qmlearn_audio_path(target_text, target_voice, allow_scan=False, use_index=True)
    rel_path = qmlearn_data_relative_path(audio_path)
    if not rel_path:
        return {}
    sound_url = qmlearn_sound_url_for_audio_path(audio_path, f"/server-data/qm-sound?path={quote(rel_path, safe='')}")
    return {
        "audio_path": sound_url,
        "audio": {"path": sound_url, "mime": "audio/mpeg", "voice": target_voice, "cached": True},
        "audio_mime": "audio/mpeg",
        "voice": target_voice,
        "voice_label": "Sound of Text | Female US" if target_voice.lower().endswith("en-us") else "Sound of Text | Female UK",
        "cached": True,
        "src": "QMLearn/Data/index",
    }


def qmlearn_audio_direct_candidates(text: object = "", voice_key: object = "") -> list[Path]:
    target_text = clean(text)
    if not target_text:
        return []
    build_sound_file_name, build_sound_storage_stem = qmlearn_audio_build_helpers()

    try:
        stem = clean(build_sound_storage_stem(target_text)) if build_sound_storage_stem else target_text
    except Exception:
        stem = target_text
    roots = [QMLEARN_DATA_ROOT]
    voice_dir = qmlearn_audio_voice_dir(voice_key)
    if voice_dir != QMLEARN_DATA_ROOT:
        roots.append(voice_dir)
    langs = qmlearn_audio_lang_candidates(voice_key)
    candidates: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path).lower()
        if key and key not in seen:
            seen.add(key)
            candidates.append(path)

    for root in roots:
        if stem:
            for ext in (".mp3", ".txt"):
                add(root / f"{stem}{ext}")
        for lang in langs:
            if not lang:
                continue
            if build_sound_file_name:
                for ext in (".mp3", ".txt"):
                    try:
                        file_name = clean(build_sound_file_name(target_text, lang, extension=ext))
                    except Exception:
                        file_name = ""
                    if file_name:
                        add(root / file_name)
            if stem:
                for ext in (".mp3", ".txt"):
                    add(root / f"{stem}_{lang}{ext}")
    return candidates


def fast_qmlearn_audio_path(text: object = "", voice_key: object = "sot:en-GB", *, allow_scan: bool = False, use_index: bool = True) -> Path | None:
    target_text = clean(text)
    target_voice = clean(voice_key) or "sot:en-GB"
    if not target_text:
        return None
    cache_key = (target_text.lower(), target_voice.lower())
    with QMLEARN_AUDIO_PATH_CACHE_LOCK:
        if cache_key in QMLEARN_AUDIO_PATH_CACHE:
            cached = QMLEARN_AUDIO_PATH_CACHE.get(cache_key)
            if cached is not None and Path(cached).is_file():
                return cached
            QMLEARN_AUDIO_PATH_CACHE.pop(cache_key, None)
    found: Path | None = None
    direct_candidates = qmlearn_audio_direct_candidates(target_text, target_voice)
    for candidate in direct_candidates:
        try:
            if candidate.is_file():
                resolved_candidate = candidate.resolve()
                resolved_candidate.relative_to(QMLEARN_DATA_ROOT.resolve())
                found = resolved_candidate
                break
        except Exception:
            continue
    if found is None and use_index:
        for candidate in direct_candidates:
            try:
                resolved_candidate = candidate.resolve()
                resolved_candidate.relative_to(QMLEARN_DATA_ROOT.resolve())
            except Exception:
                continue
            try:
                parent = resolved_candidate.parent.resolve()
                if parent != QMLEARN_DATA_ROOT.resolve():
                    indexed = qmlearn_audio_dir_index(parent).get(resolved_candidate.name.lower())
                    if indexed and indexed.is_file():
                        found = indexed
                        break
            except Exception:
                continue
    if found is not None:
        try:
            found = Path(found).resolve()
        except Exception:
            pass
    if found is not None:
        try:
            Path(found).relative_to(QMLEARN_DATA_ROOT.resolve())
        except Exception:
            found = None
    if found is not None:
        with QMLEARN_AUDIO_PATH_CACHE_LOCK:
            QMLEARN_AUDIO_PATH_CACHE[cache_key] = found
            if len(QMLEARN_AUDIO_PATH_CACHE) > 12000:
                for key in list(QMLEARN_AUDIO_PATH_CACHE.keys())[:3000]:
                    QMLEARN_AUDIO_PATH_CACHE.pop(key, None)
        return found
    if found is None and allow_scan:
        try:
            if str(PROGRAME_ROOT) not in sys.path:
                sys.path.insert(0, str(PROGRAME_ROOT))
            from module_main.Data_Input.local_sound_loader import resolve_sound_path  # noqa: PLC0415

            # Scan the voice-specific folder first. Avoid recursive full Data scans on
            # request paths; that was the main Space_V slowdown for words stored under
            # C:\QMLearn\Data\sot-en-gb / sot-en-us.
            for lang in qmlearn_audio_lang_candidates(target_voice):
                raw_path = resolve_sound_path(target_text, lang, data_dir=str(qmlearn_audio_voice_dir(target_voice)))
                if raw_path:
                    candidate = Path(raw_path)
                    try:
                        candidate.resolve().relative_to(QMLEARN_DATA_ROOT.resolve())
                    except Exception:
                        continue
                    if candidate.is_file():
                        found = candidate
                        break
        except Exception:
            found = None
    with QMLEARN_AUDIO_PATH_CACHE_LOCK:
        if found is not None:
            QMLEARN_AUDIO_PATH_CACHE[cache_key] = found
        else:
            QMLEARN_AUDIO_PATH_CACHE.pop(cache_key, None)
        if len(QMLEARN_AUDIO_PATH_CACHE) > 12000:
            for key in list(QMLEARN_AUDIO_PATH_CACHE.keys())[:3000]:
                QMLEARN_AUDIO_PATH_CACHE.pop(key, None)
    return found


def normalize_space_v_refresh_voice(voice_key: object = "") -> str:
    raw = clean(voice_key).strip().lower()
    if raw in {"us", "en-us", "sot:en-us", "sot-en-us"}:
        return "sot:en-US"
    if raw in {"uk", "gb", "en-gb", "en-uk", "sot:en-gb", "sot:en-uk", "sot-en-gb", "sot-en-uk"}:
        return "sot:en-GB"
    raise RuntimeError("Chi ho tro sua audio UK/US cho Space_V.")


class SpaceVAudioRefreshRateLimitError(RuntimeError):
    def __init__(self, retry_after: float = 0.0, *, limit: int = 20):
        self.retry_after = max(0.0, float(retry_after or 0.0))
        self.limit = max(1, int(limit or 20))
        super().__init__(f"Moi user chi duoc sua {self.limit} audio Space_V moi ngay. Admin khong bi gioi han.")


def space_v_audio_refresh_day_key(now: float | None = None) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(float(now or time.time())))


def reserve_space_v_audio_refresh_quota(actor: str, *, admin: bool = False, now: float | None = None) -> tuple[str, int, int]:
    if admin:
        limit = int(globals().get("SPACE_V_AUDIO_REFRESH_DAILY_LIMIT", 20) or 20)
        return space_v_audio_refresh_day_key(now), limit, limit
    current_time = float(now or time.time())
    day_key = space_v_audio_refresh_day_key(current_time)
    limit = max(1, int(globals().get("SPACE_V_AUDIO_REFRESH_DAILY_LIMIT", 20) or 20))
    with SPACE_V_AUDIO_REFRESH_RATE_LOCK:
        usage = SPACE_V_AUDIO_REFRESH_RATE.get(actor)
        if not isinstance(usage, dict) or clean(usage.get("day", "")) != day_key:
            usage = {"day": day_key, "count": 0}
        count = max(0, int(usage.get("count", 0) or 0))
        if count >= limit:
            raise SpaceVAudioRefreshRateLimitError(0.0, limit=limit)
        count += 1
        SPACE_V_AUDIO_REFRESH_RATE[actor] = {"day": day_key, "count": count, "updated_at": current_time}
        if len(SPACE_V_AUDIO_REFRESH_RATE) > 2000:
            for key, value in list(SPACE_V_AUDIO_REFRESH_RATE.items()):
                if not isinstance(value, dict) or clean(value.get("day", "")) != day_key:
                    SPACE_V_AUDIO_REFRESH_RATE.pop(key, None)
        return day_key, limit, max(0, limit - count)


def release_space_v_audio_refresh_quota(actor: str, day_key: str, *, admin: bool = False) -> None:
    if admin:
        return
    with SPACE_V_AUDIO_REFRESH_RATE_LOCK:
        usage = SPACE_V_AUDIO_REFRESH_RATE.get(actor)
        if isinstance(usage, dict) and clean(usage.get("day", "")) == clean(day_key):
            count = max(0, int(usage.get("count", 0) or 0) - 1)
            if count:
                usage["count"] = count
                usage["updated_at"] = time.time()
                SPACE_V_AUDIO_REFRESH_RATE[actor] = usage
            else:
                SPACE_V_AUDIO_REFRESH_RATE.pop(actor, None)


def invalidate_qmlearn_audio_path_cache(text: object = "", voice_key: object = "") -> None:
    target_text = clean(text)
    target_voice = clean(voice_key) or "sot:en-GB"
    if target_text:
        with QMLEARN_AUDIO_PATH_CACHE_LOCK:
            QMLEARN_AUDIO_PATH_CACHE.pop((target_text.lower(), target_voice.lower()), None)
        for candidate in qmlearn_audio_direct_candidates(target_text, target_voice):
            rel_path = qmlearn_data_relative_path(candidate)
            if rel_path:
                with QMLEARN_AUDIO_URL_CACHE_LOCK:
                    QMLEARN_AUDIO_URL_CACHE.pop(rel_path.lower(), None)
    try:
        voice_dir = qmlearn_audio_voice_dir(target_voice).resolve()
        with QMLEARN_AUDIO_DIR_INDEX_LOCK:
            QMLEARN_AUDIO_DIR_INDEX.pop(str(voice_dir).lower(), None)
    except Exception:
        pass


def invalidate_space_v_audio_payload_cache_for_word(word: object = "") -> int:
    target = clean(word).lower()
    if not target:
        return 0
    needle = target.encode("utf-8", errors="ignore")
    if not needle:
        return 0
    removed = 0
    try:
        with SPACE_V_QMDICT_PAYLOAD_CACHE_LOCK:
            for cache_key, row in list(SPACE_V_QMDICT_PAYLOAD_CACHE.items()):
                data = row.get("data") if isinstance(row, dict) else None
                if isinstance(data, bytes) and needle in data.lower():
                    SPACE_V_QMDICT_PAYLOAD_CACHE.pop(cache_key, None)
                    removed += 1
    except Exception:
        return removed
    return removed


def space_v_audio_refresh_result_payload(
    target_word: str,
    target_voice: str,
    audio_path: object = None,
    *,
    invalidated_payloads: int = 0,
    quota: dict | None = None,
    coalesced: bool = False,
) -> dict:
    short_key = "us" if target_voice.lower().endswith("en-us") else "uk"
    rel_path = qmlearn_data_relative_path(audio_path)
    version = int(time.time() * 1000)
    try:
        if audio_path and Path(audio_path).is_file():
            version = int(Path(audio_path).stat().st_mtime_ns)
    except Exception:
        pass
    if rel_path:
        clip = {
            "m": "audio/mpeg",
            "u": f"/server-data/qm-sound?path={quote(rel_path, safe='')}&v={version}",
            "src": "QMLearn/Data/refreshed",
            "voice": target_voice,
        }
    else:
        clip = {
            "m": "audio/mpeg",
            "u": f"/server-data/qm-sound?word={quote(target_word, safe='')}&voice={quote(target_voice, safe='')}&v={version}",
            "src": "QMLearn/Data/refreshed-lazy",
            "voice": target_voice,
        }
    return {
        "word": target_word,
        "voice": target_voice,
        "short_key": short_key,
        "clip": clip,
        "audio": {target_voice: clip, target_voice.lower(): clip, short_key: clip},
        "refreshed_at": utc_timestamp(),
        "cache": {"invalidated_space_v_payloads": int(invalidated_payloads or 0), "coalesced": bool(coalesced)},
        "quota": quota or {},
    }


def wait_for_space_v_audio_refresh_singleflight(target_word: str, target_voice: str, timeout_seconds: float = 18.0) -> dict | None:
    key = (clean(target_word).lower(), clean(target_voice).lower())
    deadline = time.time() + max(1.0, float(timeout_seconds or 18.0))
    with SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT_LOCK:
        row = SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT.get(key)
        if not isinstance(row, dict):
            row = {"condition": threading.Condition(SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT_LOCK), "running": False, "waiters": 0}
            SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT[key] = row
        condition = row.get("condition")
        if not row.get("running"):
            row["running"] = True
            row["waiters"] = 0
            row["started_at"] = time.time()
            return None
        row["waiters"] = int(row.get("waiters", 0) or 0) + 1
        while row.get("running"):
            remaining = deadline - time.time()
            if remaining <= 0:
                return {"timeout": True}
            condition.wait(min(remaining, 0.5))
        result = row.get("result") if isinstance(row.get("result"), dict) else None
        error = clean(row.get("error", ""))
        if result:
            out = dict(result)
            cache = dict(out.get("cache") if isinstance(out.get("cache"), dict) else {})
            cache["coalesced"] = True
            out["cache"] = cache
            return out
        if error:
            raise RuntimeError(error)
        return {"timeout": True}


def finish_space_v_audio_refresh_singleflight(target_word: str, target_voice: str, result: dict | None = None, error: object = "") -> None:
    key = (clean(target_word).lower(), clean(target_voice).lower())
    with SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT_LOCK:
        row = SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT.get(key)
        if not isinstance(row, dict):
            return
        row["running"] = False
        if result:
            row["result"] = dict(result)
        if error:
            row["error"] = clean(error)
        condition = row.get("condition")
        if condition:
            condition.notify_all()
        if not int(row.get("waiters", 0) or 0):
            SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT.pop(key, None)
        elif len(SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT) > 512:
            now = time.time()
            for old_key, old_row in list(SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT.items()):
                if not isinstance(old_row, dict) or (not old_row.get("running") and now - float(old_row.get("started_at", now) or now) > 60.0):
                    SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT.pop(old_key, None)


def acquire_space_v_audio_refresh_slot(timeout_seconds: float = 30.0) -> bool:
    timeout_value = max(1.0, float(timeout_seconds or 30.0))
    try:
        return bool(SPACE_V_AUDIO_REFRESH_SEMAPHORE.acquire(timeout=timeout_value))
    except TypeError:
        deadline = time.time() + timeout_value
        while time.time() < deadline:
            if SPACE_V_AUDIO_REFRESH_SEMAPHORE.acquire(False):
                return True
            time.sleep(0.05)
        return False


def release_space_v_audio_refresh_slot() -> None:
    try:
        SPACE_V_AUDIO_REFRESH_SEMAPHORE.release()
    except Exception:
        pass


def refresh_space_v_word_audio(username: object = "", word: object = "", voice_key: object = "", *, admin: bool = False) -> dict:
    actor = normalize_username(username)
    target_word = clean(word)
    target_voice = normalize_space_v_refresh_voice(voice_key)
    if not actor:
        raise RuntimeError("Chua dang nhap.")
    if not target_word:
        raise RuntimeError("Thieu tu vung can sua audio.")
    singleflight_wait = wait_for_space_v_audio_refresh_singleflight(target_word, target_voice)
    if singleflight_wait:
        if singleflight_wait.get("timeout"):
            audio_path = fast_qmlearn_audio_path(target_word, target_voice, allow_scan=True, use_index=False)
            if audio_path:
                return space_v_audio_refresh_result_payload(target_word, target_voice, audio_path, coalesced=True)
            raise RuntimeError("Dang co may khac sua audio tu nay, hay thu lai sau vai giay.")
        return singleflight_wait
    now = time.time()
    try:
        day_key, daily_limit, remaining = reserve_space_v_audio_refresh_quota(actor, admin=admin, now=now)
    except Exception as exc:
        finish_space_v_audio_refresh_singleflight(target_word, target_voice, error=str(exc))
        raise
    invalidate_qmlearn_audio_path_cache(target_word, target_voice)
    slot_acquired = acquire_space_v_audio_refresh_slot()
    if not slot_acquired:
        release_space_v_audio_refresh_quota(actor, day_key, admin=admin)
        message = "Server dang sua nhieu audio Space_V. Hay thu lai sau vai giay."
        finish_space_v_audio_refresh_singleflight(target_word, target_voice, error=message)
        raise RuntimeError(message)
    try:
        audio_bytes = synthesize_space_v_sound_of_text_bytes(
            target_word,
            target_voice,
            lambda message: stt_debug_log("space_v_audio_refresh", username=actor, word=target_word, voice=target_voice, message=message),
        )
        saved_path = force_save_space_v_sound_audio(
            target_word,
            target_voice,
            audio_bytes,
            lambda message: stt_debug_log("space_v_audio_refresh", username=actor, word=target_word, voice=target_voice, message=message),
        )
    except Exception as exc:
        release_space_v_audio_refresh_quota(actor, day_key, admin=admin)
        finish_space_v_audio_refresh_singleflight(target_word, target_voice, error=f"Khong sua duoc audio Space_V: {exc}")
        raise RuntimeError(f"Khong sua duoc audio Space_V: {exc}") from exc
    finally:
        release_space_v_audio_refresh_slot()
    try:
        invalidate_qmlearn_audio_path_cache(target_word, target_voice)
        invalidated_payloads = invalidate_space_v_audio_payload_cache_for_word(target_word)
        audio_path = saved_path if saved_path and Path(saved_path).is_file() else fast_qmlearn_audio_path(target_word, target_voice, allow_scan=True, use_index=False)
        result = space_v_audio_refresh_result_payload(
            target_word,
            target_voice,
            audio_path,
            invalidated_payloads=invalidated_payloads,
            quota={"limit": daily_limit, "remaining": remaining, "admin": bool(admin), "day": day_key},
        )
        finish_space_v_audio_refresh_singleflight(target_word, target_voice, result=result)
        return result
    except Exception as exc:
        finish_space_v_audio_refresh_singleflight(target_word, target_voice, error=str(exc))
        raise


def qmdict_word_audio_refresh_entries(mode: str = "all") -> list[tuple[str, str, str]]:
    clean_mode = clean(mode).strip().lower()
    entries: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    if clean_mode in {"failed", "retry", "retry-failed"}:
        try:
            payload = json.loads(QMDICT_WORD_AUDIO_REFRESH_REPORT_FILE.read_text(encoding="utf-8-sig", errors="replace"))
            rows = payload.get("items", []) if isinstance(payload, dict) else []
            if not isinstance(rows, list):
                rows = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                status = clean(row.get("status", "")).lower()
                if status not in {"failed", "missing"}:
                    continue
                word = clean(row.get("word") or row.get("key") or "")
                try:
                    voice = normalize_space_v_refresh_voice(row.get("voice", ""))
                except Exception:
                    continue
                pair = (word.lower(), voice.lower())
                if word and pair not in seen:
                    seen.add(pair)
                    entries.append((word.upper(), word, voice))
        except Exception:
            entries = []
        return entries
    _runtime, qmdict = qmdict_runtime_and_dict()
    for raw_key, _raw_row in list(qmdict.items()):
        word = clean(raw_key)
        if not word:
            continue
        for voice in ("sot:en-GB", "sot:en-US"):
            pair = (word.lower(), voice.lower())
            if pair in seen:
                continue
            seen.add(pair)
            entries.append((word.upper(), word, voice))
    return entries


def refresh_qmdict_word_audio_item(key: object = "", word: object = "", voice_key: object = "") -> dict:
    target_key = clean(key).upper()
    target_word = clean(word)
    target_voice = normalize_space_v_refresh_voice(voice_key)
    row = {"key": target_key or target_word.upper(), "word": target_word, "voice": target_voice, "status": ""}
    if not target_word:
        row.update({"status": "failed", "error": "Missing QmDict word."})
        return row
    last_error = ""
    for attempt in range(1, 4):
        try:
            invalidate_qmlearn_audio_path_cache(target_word, target_voice)
            from future_vocab_builder_gui import force_save_local_sound_bytes, synthesize_sound_of_text_reliable  # noqa: PLC0415

            audio_bytes = synthesize_sound_of_text_reliable(
                target_word,
                target_voice,
                lambda message: stt_debug_log("qmdict_word_audio_refresh", key=target_key, word=target_word, voice=target_voice, attempt=attempt, message=message),
            )
            saved_path = force_save_local_sound_bytes(
                target_word,
                target_voice,
                audio_bytes,
                lambda message: stt_debug_log("qmdict_word_audio_refresh", key=target_key, word=target_word, voice=target_voice, attempt=attempt, message=message),
            )
            invalidate_qmlearn_audio_path_cache(target_word, target_voice)
            audio_path = saved_path if saved_path and Path(saved_path).is_file() else fast_qmlearn_audio_path(target_word, target_voice, allow_scan=True, use_index=False)
            if audio_path is not None and Path(audio_path).is_file():
                row.update({"status": "refreshed", "path": qmlearn_data_relative_path(audio_path), "attempts": attempt})
                return row
            raise RuntimeError("Audio file was not saved after synthesis.")
        except Exception as exc:
            last_error = str(exc)
            if attempt < 3:
                time.sleep(0.7 * attempt)
    row.update({"status": "failed", "error": last_error or "Unknown audio refresh error.", "attempts": 3})
    return row


def run_qmdict_word_audio_refresh_job(job_id: str, mode: str = "all") -> None:
    done = refreshed = failed = scanned = 0
    report_rows: list[dict] = []
    try:
        ensure_qmdict_runtime_fresh(force=True)
        entries = qmdict_word_audio_refresh_entries(mode)
        total = len(entries)
        worker_count = min(QMDICT_WORD_AUDIO_REFRESH_MAX_WORKERS, total) if total else 0
        with QMDICT_WORD_AUDIO_REFRESH_LOCK:
            QMDICT_WORD_AUDIO_REFRESH_JOB.update(
                {
                    "phase": "downloading" if total else "complete",
                    "message": f"Refreshing QmDict UK/US word audio with {worker_count} workers." if total else "No QmDict word audio needs retry.",
                    "scan_total": total,
                    "scan_done": total,
                    "workers": worker_count,
                    "total": total,
                    "done": 0,
                    "refreshed": 0,
                    "failed": 0,
                    "last_key": "",
                    "last_word": "",
                    "last_voice": "",
                    "updated_at": utc_timestamp(),
                    "error": "",
                }
            )
            snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
        write_qmdict_word_audio_refresh_progress({"version": 1, **snapshot})
        if entries:
            with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="qmdict-word-audio") as executor:
                future_map = {executor.submit(refresh_qmdict_word_audio_item, key, word, voice): (key, word, voice) for key, word, voice in entries}
                for future in concurrent.futures.as_completed(future_map):
                    key, word, voice = future_map[future]
                    done += 1
                    scanned += 1
                    try:
                        row = future.result()
                    except Exception as exc:
                        row = {"key": key, "word": word, "voice": voice, "status": "failed", "error": str(exc)}
                    status = clean(row.get("status", "")).lower()
                    if status == "refreshed":
                        refreshed += 1
                    else:
                        failed += 1
                    report_rows.append(row)
                    with QMDICT_WORD_AUDIO_REFRESH_LOCK:
                        QMDICT_WORD_AUDIO_REFRESH_JOB.update(
                            {
                                "done": done,
                                "scan_done": scanned,
                                "refreshed": refreshed,
                                "failed": failed,
                                "last_key": clean(row.get("key") or key),
                                "last_word": clean(row.get("word") or word)[:180],
                                "last_voice": clean(row.get("voice") or voice),
                                "updated_at": utc_timestamp(),
                            }
                        )
                        snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
                    if done == total or done % 10 == 0 or status != "refreshed":
                        write_qmdict_word_audio_refresh_progress({"version": 1, **snapshot})
        completed_at = utc_timestamp()
        with QMDICT_WORD_AUDIO_REFRESH_LOCK:
            QMDICT_WORD_AUDIO_REFRESH_JOB.update(
                {
                    "running": False,
                    "phase": "complete",
                    "message": "QmDict UK/US word audio refresh complete.",
                    "completed_at": completed_at,
                    "updated_at": completed_at,
                }
            )
            final_snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
        atomic_write_json(
            QMDICT_WORD_AUDIO_REFRESH_REPORT_FILE,
            {"version": 1, **final_snapshot, "items": report_rows[-5000:]},
            indent=2,
        )
        write_qmdict_word_audio_refresh_progress({"version": 1, **final_snapshot})
        stt_debug_log("qmdict_word_audio_refresh_done", job_id=job_id, mode=mode, total=total, refreshed=refreshed, failed=failed)
    except Exception as exc:
        with QMDICT_WORD_AUDIO_REFRESH_LOCK:
            QMDICT_WORD_AUDIO_REFRESH_JOB.update(
                {
                    "running": False,
                    "phase": "failed",
                    "message": "QmDict UK/US word audio refresh failed.",
                    "updated_at": utc_timestamp(),
                    "error": str(exc),
                }
            )
            snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
        write_qmdict_word_audio_refresh_progress({"version": 1, **snapshot})
        stt_debug_log("qmdict_word_audio_refresh_failed", job_id=job_id, mode=mode, error=str(exc))


def start_qmdict_word_audio_refresh(mode: str = "all") -> dict:
    clean_mode = clean(mode).strip().lower() or "all"
    if clean_mode not in {"all", "failed", "retry", "retry-failed"}:
        clean_mode = "all"
    if clean_mode in {"retry", "retry-failed"}:
        clean_mode = "failed"
    with QMDICT_WORD_AUDIO_REFRESH_LOCK:
        if QMDICT_WORD_AUDIO_REFRESH_JOB.get("running"):
            return {"started": False, "word_audio_refresh": dict(QMDICT_WORD_AUDIO_REFRESH_JOB)}
        job_id = uuid.uuid4().hex
        started_at = utc_timestamp()
        QMDICT_WORD_AUDIO_REFRESH_JOB.update(
            {
                "running": True,
                "job_id": job_id,
                "mode": clean_mode,
                "phase": "queued",
                "message": "Waiting to refresh QmDict UK/US word audio.",
                "started_at": started_at,
                "updated_at": started_at,
                "completed_at": "",
                "scan_total": 0,
                "scan_done": 0,
                "workers": 0,
                "total": 0,
                "done": 0,
                "refreshed": 0,
                "failed": 0,
                "last_key": "",
                "last_word": "",
                "last_voice": "",
                "error": "",
            }
        )
        snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
    threading.Thread(
        target=run_qmdict_word_audio_refresh_job,
        args=(job_id, clean_mode),
        name=f"qmdict-word-audio-refresh-{job_id[:8]}",
        daemon=True,
    ).start()
    write_qmdict_word_audio_refresh_progress({"version": 1, **snapshot})
    return {"started": True, "word_audio_refresh": snapshot}


def qmdict_meaning_audio_local_path(meaning: object = "") -> Path | None:
    text = clean(meaning)
    if not text:
        return None
    path = fast_qmlearn_audio_path(text, "sot:vi-VN")
    if path is not None and Path(path).is_file():
        return Path(path)
    try:
        _file_name_builder, build_sound_storage_stem = qmlearn_audio_build_helpers()
        stem = build_sound_storage_stem(text) if build_sound_storage_stem else ""
        if stem:
            for suffix in (".mp3", ".txt"):
                candidate = Path(r"C:\QMLearn\Data") / f"{stem}{suffix}"
                if candidate.is_file():
                    return candidate
    except Exception:
        pass
    return None


def ensure_qmlearn_data_sound_plain_mp3(target: Path | None) -> Path | None:
    if target is None:
        return None
    path = Path(target)
    try:
        path.resolve().relative_to(QMLEARN_DATA_ROOT.resolve())
    except Exception:
        return None
    if not path.is_file() or path.suffix.lower() not in {".mp3", ".txt"}:
        return None
    try:
        from module_main.Data_Input.local_sound_loader import read_sound_file_bytes, plain_mp3_path_for, audio_bytes_look_like_mp3  # noqa: PLC0415

        raw = path.read_bytes()
        if path.suffix.lower() == ".mp3" and audio_bytes_look_like_mp3(raw):
            return path
        audio_bytes = read_sound_file_bytes(path, migrate=True)
        if not audio_bytes or not audio_bytes_look_like_mp3(audio_bytes):
            return path
        mp3_path = Path(plain_mp3_path_for(path))
        if mp3_path.is_file():
            return mp3_path
        return path
    except Exception as exc:
        stt_debug_log("qmlearn_audio_plain_mp3_migrate_failed", path=str(path), error=str(exc))
    return path


def qmdict_meaning_audio_dynamic_clip(meaning: object = "") -> dict:
    text = clean(meaning)
    if not text or not qmdict_meaning_has_local_audio_stem(text, qmdict_audio_stem_index_shared()):
        return {}
    return {
        "m": "audio/mpeg",
        "u": f"/server-data/qm-sound?meaning={quote(text, safe='')}",
        "aid": f"v1:m:{hashlib.sha256(text.lower().encode('utf-8')).hexdigest()[:32]}",
        "src": "QMLearn/Data/meaning-lazy",
    }


def qmlearn_sound_url_for_audio_path(audio_path: object = None, fallback_query: str = "") -> str:
    rel_path = qmlearn_data_relative_path(audio_path)
    if rel_path:
        cache_key = rel_path.lower()
        with QMLEARN_AUDIO_URL_CACHE_LOCK:
            cached = QMLEARN_AUDIO_URL_CACHE.get(cache_key)
            if cached and cached[1]:
                return cached[1]
        version = 0
        try:
            version = int(Path(audio_path).stat().st_mtime)
        except Exception:
            version = 0
        suffix = f"&v={version}" if version else ""
        url = f"/server-data/qm-sound?path={quote(rel_path, safe='')}{suffix}"
        if version:
            with QMLEARN_AUDIO_URL_CACHE_LOCK:
                QMLEARN_AUDIO_URL_CACHE[cache_key] = (version, url)
                if len(QMLEARN_AUDIO_URL_CACHE) > 20000:
                    for key in list(QMLEARN_AUDIO_URL_CACHE.keys())[:5000]:
                        QMLEARN_AUDIO_URL_CACHE.pop(key, None)
        return url
    return fallback_query


def qmdict_space_v_dynamic_audio_map(word: object = "", meaning: object = "") -> dict:
    target_word = clean(word)
    audio: dict[str, dict] = {}
    try:
        for _label, voice_key, short_key in SPACE_V_DEFAULT_VOICES:
            if target_word:
                # Added 2026-07-21: resolve audio only when the client plays/prefetches it, not while opening every word in the lesson.
                normalized_voice = clean(voice_key)
                sound_url = f"/server-data/qm-sound?word={quote(target_word, safe='')}&voice={quote(normalized_voice, safe='')}"
                clip = {
                    "m": "audio/mpeg",
                    "u": sound_url,
                    "aid": f"v1:w:{vocab_key(target_word)}:{'u' if normalized_voice.lower().endswith('en-us') else 'g'}",
                    "src": "QMLearn/Data/lazy",
                }
                audio[voice_key] = clip
                audio[short_key] = clip
        meaning_clip = qmdict_meaning_audio_dynamic_clip(meaning)
        if meaning_clip:
            audio["sot:vi-VN"] = meaning_clip
            audio["vi-VN"] = meaning_clip
            audio["vi"] = meaning_clip
    except Exception:
        pass
    return audio


def qmdict_space_v_dynamic_detail(word: object = "", summary: object = None) -> dict:
    target_word = clean(word)
    if not target_word:
        return {}
    source = summary if isinstance(summary, dict) else qmdict_lookup_summary_queued(target_word)
    if not isinstance(source, dict) or not source:
        return {}
    items: list[dict] = []
    word_type = clean(source.get("type", ""))
    meaning = clean(source.get("meaning", ""))
    pron = clean(source.get("pron", ""))
    usage = clean(source.get("usage", ""))
    if word_type:
        items.append({"k": "pos", "t": word_type})
    if meaning:
        items.append({"k": "def", "t": meaning})
    if pron:
        items.append({"k": "ipa", "t": f"IPA {pron}"})
    if usage:
        items.append({"k": "note", "t": usage})
    examples = source.get("examples", [])
    if isinstance(examples, str):
        examples = [examples] if clean(examples) else []
    for sample in list(examples if isinstance(examples, list) else [])[:4]:
        if isinstance(sample, dict):
            en = clean(sample.get("en") or sample.get("e") or sample.get("text") or sample.get("sentence") or "")
            vi = clean(sample.get("vi") or sample.get("v") or sample.get("meaning") or sample.get("translation") or "")
        else:
            raw = clean(sample)
            en, vi = (raw.split("+", 1) + [""])[:2] if "+" in raw else (raw, "")
        if en or vi:
            items.append({"k": "ex", "e": en, "v": vi})
        if len(items) >= 8:
            break
    return {"src": "qmdict", "key": target_word, "items": items} if items else {}


SPACE_V_DYNAMIC_IMAGE_CACHE_LOCK = threading.Lock()
SPACE_V_DYNAMIC_IMAGE_CACHE: dict[str, dict] = {}
SPACE_V_DYNAMIC_IMAGE_POSTGRES_LOADED = False
SPACE_V_DYNAMIC_IMAGE_INFLIGHT: dict[str, float] = {}
SPACE_V_DYNAMIC_IMAGE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=6, thread_name_prefix="space-v-image-fetch")
SPACE_V_DYNAMIC_IMAGE_CACHE_MAX = 2048
SPACE_V_DYNAMIC_IMAGE_INFLIGHT_MAX = 512
SPACE_V_DYNAMIC_IMAGE_POSITIVE_TTL_SECONDS = 86400.0
SPACE_V_DYNAMIC_IMAGE_NEGATIVE_TTL_SECONDS = 600.0
SPACE_V_DYNAMIC_IMAGE_POSTGRES_LOCK = threading.Lock()
SPACE_V_DYNAMIC_IMAGE_POSTGRES_PENDING: dict[str, dict] = {}
SPACE_V_DYNAMIC_IMAGE_POSTGRES_SCHEDULED = False
SPACE_V_IMAGE_PREFETCH_LOCK = threading.Lock()
SPACE_V_IMAGE_PREFETCH_PENDING: dict[str, str] = {}
SPACE_V_IMAGE_PREFETCH_ACTIVE_KEYS: set[str] = set()
SPACE_V_IMAGE_PREFETCH_SCHEDULED = False
SPACE_V_IMAGE_PREFETCH_MAX_PENDING = 192
SPACE_V_IMAGE_PREFETCH_BATCH_SIZE = 12
SPACE_V_IMAGE_PREFETCH_MAX_INFLIGHT = 12


def _space_v_dynamic_image_cached_row(key: str) -> dict | None:
    global SPACE_V_DYNAMIC_IMAGE_POSTGRES_LOADED
    now = time.monotonic()
    with SPACE_V_DYNAMIC_IMAGE_CACHE_LOCK:
        if not SPACE_V_DYNAMIC_IMAGE_POSTGRES_LOADED:
            epoch_now = time.time()
            for stored in server_database_load_vocab_image_cache_rows(SPACE_V_DYNAMIC_IMAGE_CACHE_MAX):
                stored_key = clean(stored.get("word_key", "")).lower()
                expires_epoch = float(stored.get("expires_epoch", 0) or 0)
                if not stored_key or expires_epoch <= epoch_now:
                    continue
                SPACE_V_DYNAMIC_IMAGE_CACHE[stored_key] = {
                    "image": dict(stored.get("image") or {}),
                    "expires_at": time.monotonic() + max(0.1, expires_epoch - epoch_now),
                }
            SPACE_V_DYNAMIC_IMAGE_POSTGRES_LOADED = True
        cached = SPACE_V_DYNAMIC_IMAGE_CACHE.get(key)
        if cached and float(cached.get("expires_at", 0) or 0) > now:
            return cached
        if cached:
            SPACE_V_DYNAMIC_IMAGE_CACHE.pop(key, None)
        return None


def _queue_space_v_dynamic_image_postgres(word_key: str, image: dict, expires_epoch: float) -> None:
    global SPACE_V_DYNAMIC_IMAGE_POSTGRES_SCHEDULED
    with SPACE_V_DYNAMIC_IMAGE_POSTGRES_LOCK:
        SPACE_V_DYNAMIC_IMAGE_POSTGRES_PENDING[word_key] = {
            "word_key": word_key,
            "image": dict(image),
            "expires_epoch": float(expires_epoch),
        }
        if SPACE_V_DYNAMIC_IMAGE_POSTGRES_SCHEDULED:
            return
        SPACE_V_DYNAMIC_IMAGE_POSTGRES_SCHEDULED = True

    def worker() -> None:
        global SPACE_V_DYNAMIC_IMAGE_POSTGRES_SCHEDULED
        while True:
            time.sleep(1.0)
            with SPACE_V_DYNAMIC_IMAGE_POSTGRES_LOCK:
                batch = list(SPACE_V_DYNAMIC_IMAGE_POSTGRES_PENDING.values())
                SPACE_V_DYNAMIC_IMAGE_POSTGRES_PENDING.clear()
            try:
                server_database_store_vocab_image_cache_batch(batch)
            except Exception as exc:
                stt_debug_log("space_v_dynamic_image_cache_write_failed", error=str(exc), rows=len(batch))
            with SPACE_V_DYNAMIC_IMAGE_POSTGRES_LOCK:
                if SPACE_V_DYNAMIC_IMAGE_POSTGRES_PENDING:
                    continue
                SPACE_V_DYNAMIC_IMAGE_POSTGRES_SCHEDULED = False
                return

    threading.Thread(target=worker, name="space-v-image-cache-write", daemon=True).start()


def _fetch_space_v_dynamic_image(target_word: str, key: str) -> None:
    result: dict = {}
    ttl = SPACE_V_DYNAMIC_IMAGE_NEGATIVE_TTL_SECONDS

    try:
        query = f"q={quote(key, safe='')}&page_size=8&mature=false&format=json"
        request = Request(
            f"https://api.openverse.org/v1/images/?{query}",
            headers={"Accept": "application/json", "User-Agent": "QMLearnFutureVocabulary/1.0 (Server 2)"},
        )
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
        for item in payload.get("results") or []:
            filetype = clean(item.get("filetype", "")).lower()
            image_url = clean(item.get("thumbnail") or item.get("url") or "")
            if not image_url.startswith(("http://", "https://")) or filetype in {"tif", "tiff", "djvu"}:
                continue
            result = {
                "u": image_url,
                "s": f"Openverse/{clean(item.get('provider') or item.get('source') or 'image')}",
                "c": clean(item.get("title") or target_word),
            }
            break
        if result:
            ttl = SPACE_V_DYNAMIC_IMAGE_POSITIVE_TTL_SECONDS
    except Exception as exc:
        stt_debug_log("space_v_dynamic_image_failed", word=target_word, error=str(exc))
    finally:
        expires_epoch = time.time() + ttl
        with SPACE_V_DYNAMIC_IMAGE_CACHE_LOCK:
            SPACE_V_DYNAMIC_IMAGE_CACHE[key] = {"image": dict(result), "expires_at": time.monotonic() + ttl}
            while len(SPACE_V_DYNAMIC_IMAGE_CACHE) > SPACE_V_DYNAMIC_IMAGE_CACHE_MAX:
                SPACE_V_DYNAMIC_IMAGE_CACHE.pop(next(iter(SPACE_V_DYNAMIC_IMAGE_CACHE)), None)
            SPACE_V_DYNAMIC_IMAGE_INFLIGHT.pop(key, None)
        _queue_space_v_dynamic_image_postgres(key, result, expires_epoch)


# Added 2026-07-20: return cold image misses immediately while one bounded shared pool fetches and persists them.
def qmdict_space_v_image_lookup(word: object = "") -> dict:
    target_word = clean(word)
    key = vocab_key(target_word)
    if not key:
        return {"image": {}, "pending": False, "retry_after_ms": 0}
    cached = _space_v_dynamic_image_cached_row(key)
    if cached is not None:
        image = cached.get("image")
        return {"image": dict(image) if isinstance(image, dict) else {}, "pending": False, "retry_after_ms": 0}
    with SPACE_V_DYNAMIC_IMAGE_CACHE_LOCK:
        if key in SPACE_V_DYNAMIC_IMAGE_INFLIGHT:
            return {"image": {}, "pending": True, "retry_after_ms": 1400}
        if len(SPACE_V_DYNAMIC_IMAGE_INFLIGHT) >= SPACE_V_DYNAMIC_IMAGE_INFLIGHT_MAX:
            return {"image": {}, "pending": True, "retry_after_ms": 5000}
        SPACE_V_DYNAMIC_IMAGE_INFLIGHT[key] = time.monotonic()
    SPACE_V_DYNAMIC_IMAGE_EXECUTOR.submit(_fetch_space_v_dynamic_image, target_word, key)
    return {"image": {}, "pending": True, "retry_after_ms": 1400}


def qmdict_space_v_dynamic_image(word: object = "") -> dict:
    return dict(qmdict_space_v_image_lookup(word).get("image") or {})


def load_space_v_image_cache_light() -> dict:
    try:
        stat = VOCAB_IMAGE_CACHE_FILE.stat()
        signature = (int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        signature = (0, -1)
    with SPACE_V_IMAGE_CACHE_LOCK:
        if SPACE_V_IMAGE_CACHE_STATE.get("signature") == signature:
            cached_payload = SPACE_V_IMAGE_CACHE_STATE.get("payload")
            return cached_payload if isinstance(cached_payload, dict) else {}
        payload = {}
        if signature[1] >= 0:
            try:
                loaded = json.loads(VOCAB_IMAGE_CACHE_FILE.read_text(encoding="utf-8-sig", errors="replace"))
                payload = loaded if isinstance(loaded, dict) else {}
            except Exception:
                payload = {}
        SPACE_V_IMAGE_CACHE_STATE["signature"] = signature
        SPACE_V_IMAGE_CACHE_STATE["payload"] = payload
        return payload


def qmdict_space_v_cached_image(word: object = "") -> dict:
    target_word = clean(word)
    key = vocab_key(target_word)
    if not key:
        return {}
    try:
        cache = load_space_v_image_cache_light()
        cached = dict(cache.get(key) or {}) if isinstance(cache, dict) else {}
        return cached if clean(cached.get("u") or cached.get("url") or "") else {}
    except Exception:
        return {}


def prefetch_space_v_images_for_entries(entries: object, limit: int = 120) -> None:
    global SPACE_V_IMAGE_PREFETCH_SCHEDULED
    words: list[str] = []
    seen: set[str] = set()
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, dict):
            word = clean(entry.get("word") or entry.get("w") or entry.get("en") or entry.get("e") or "")
        else:
            word = clean(getattr(entry, "word", ""))
        key = vocab_key(word)
        if not key or key in seen:
            continue
        seen.add(key)
        words.append(word)
        if len(words) >= min(24, max(1, int(limit or 120))):
            break
    if not words:
        return
    with SPACE_V_IMAGE_PREFETCH_LOCK:
        for word in words:
            key = vocab_key(word)
            if not key or key in SPACE_V_IMAGE_PREFETCH_ACTIVE_KEYS:
                continue
            if len(SPACE_V_IMAGE_PREFETCH_PENDING) >= SPACE_V_IMAGE_PREFETCH_MAX_PENDING:
                break
            SPACE_V_IMAGE_PREFETCH_PENDING[key] = word
            SPACE_V_IMAGE_PREFETCH_ACTIVE_KEYS.add(key)
        if SPACE_V_IMAGE_PREFETCH_SCHEDULED or not SPACE_V_IMAGE_PREFETCH_PENDING:
            return
        SPACE_V_IMAGE_PREFETCH_SCHEDULED = True

    # One coalesced worker prevents every opened file from creating its own thread pool.
    def worker() -> None:
        global SPACE_V_IMAGE_PREFETCH_SCHEDULED
        try:
            while True:
                with SPACE_V_IMAGE_PREFETCH_LOCK:
                    batch = list(SPACE_V_IMAGE_PREFETCH_PENDING.items())[:SPACE_V_IMAGE_PREFETCH_BATCH_SIZE]
                    for key, _word in batch:
                        SPACE_V_IMAGE_PREFETCH_PENDING.pop(key, None)
                    if not batch:
                        SPACE_V_IMAGE_PREFETCH_SCHEDULED = False
                        return
                postponed: list[tuple[str, str]] = []
                for key, word in batch:
                    with SPACE_V_DYNAMIC_IMAGE_CACHE_LOCK:
                        saturated = len(SPACE_V_DYNAMIC_IMAGE_INFLIGHT) >= SPACE_V_IMAGE_PREFETCH_MAX_INFLIGHT
                    if saturated:
                        postponed.append((key, word))
                        continue
                    try:
                        qmdict_space_v_dynamic_image(word)
                    except Exception:
                        pass
                    finally:
                        with SPACE_V_IMAGE_PREFETCH_LOCK:
                            SPACE_V_IMAGE_PREFETCH_ACTIVE_KEYS.discard(key)
                if postponed:
                    with SPACE_V_IMAGE_PREFETCH_LOCK:
                        for key, word in postponed:
                            if len(SPACE_V_IMAGE_PREFETCH_PENDING) >= SPACE_V_IMAGE_PREFETCH_MAX_PENDING:
                                break
                            SPACE_V_IMAGE_PREFETCH_PENDING.setdefault(key, word)
                time.sleep(0.25 if postponed else 0.08)
        except Exception as exc:
            stt_debug_log("space_v_image_prefetch_failed", error=str(exc))
            with SPACE_V_IMAGE_PREFETCH_LOCK:
                SPACE_V_IMAGE_PREFETCH_SCHEDULED = False

    threading.Thread(target=worker, name="space-v-image-prefetch", daemon=True).start()


def space_v_audio_clip_signature(clip: object = None) -> str:
    if not isinstance(clip, dict):
        return ""
    url = clean(clip.get("u") or clip.get("url") or clip.get("src") or clip.get("path"))
    mime = clean(clip.get("m") or clip.get("mime") or "audio/mpeg")
    base64_value = clean(clip.get("b") or clip.get("base64") or clip.get("data"))
    return json.dumps({"m": mime, "u": url, "b": base64_value[:64], "bl": len(base64_value)}, ensure_ascii=False, sort_keys=True)


def qmdict_audio_refresh_entries(keys: object = None) -> list[tuple[str, str]]:
    key_filter = {clean(key).upper() for key in keys or [] if clean(key)} if isinstance(keys, (list, tuple, set)) else set()
    _runtime, qmdict = qmdict_runtime_and_dict()
    entries: list[tuple[str, str]] = []
    seen_meanings: set[str] = set()
    for raw_key, raw_row in list(qmdict.items()):
        key = clean(raw_key).upper()
        if key_filter and key not in key_filter:
            continue
        if isinstance(raw_row, dict):
            meaning = clean(raw_row.get("meaning", ""))
        elif isinstance(raw_row, (list, tuple)) and len(raw_row) > 1:
            meaning = clean(raw_row[1])
        else:
            meaning = ""
        if not meaning:
            continue
        meaning_key = re.sub(r"\s+", " ", meaning).strip().lower()
        if not meaning_key or meaning_key in seen_meanings:
            continue
        seen_meanings.add(meaning_key)
        entries.append((key, meaning))
    return entries


def qmdict_audio_stem_index_shared(force: bool = False) -> set[str]:
    with QMDICT_AUDIO_STEM_INDEX_LOCK:
        cached_stems = QMDICT_AUDIO_STEM_INDEX_CACHE.get("stems")
        if (not force) and isinstance(cached_stems, set) and cached_stems:
            return cached_stems
        if not force:
            try:
                payload = json.loads(QMLEARN_AUDIO_STEM_INDEX_FILE.read_text(encoding="utf-8"))
                raw_stems = payload.get("stems") if isinstance(payload, dict) else None
                if isinstance(raw_stems, list) and raw_stems:
                    stems_from_file = {clean(item) for item in raw_stems if clean(item)}
                    QMDICT_AUDIO_STEM_INDEX_CACHE["stems"] = stems_from_file
                    QMDICT_AUDIO_STEM_INDEX_CACHE["loaded_at"] = time.time()
                    return stems_from_file
            except Exception:
                pass
    stems: set[str] = set()
    try:
        root = QMLEARN_DATA_ROOT
        if not root.is_dir():
            return stems
        for pattern in ("*.mp3", "*.txt"):
            for path in root.glob(pattern):
                if not path.is_file():
                    continue
                stem = clean(path.stem)
                if not stem:
                    continue
                stems.add(stem)
                base_stem = re.sub(r"_(?:vi-vn|vi)$", "", stem, flags=re.I)
                if base_stem:
                    stems.add(base_stem)
    except Exception as exc:
        stt_debug_log("qmdict_audio_stem_index_failed", error=str(exc))
    if stems:
        with QMDICT_AUDIO_STEM_INDEX_LOCK:
            QMDICT_AUDIO_STEM_INDEX_CACHE["stems"] = set(stems)
            QMDICT_AUDIO_STEM_INDEX_CACHE["loaded_at"] = time.time()
        try:
            atomic_write_json(
                QMLEARN_AUDIO_STEM_INDEX_FILE,
                {"version": 1, "updated_at": utc_timestamp(), "count": len(stems), "stems": sorted(stems)},
                indent=None,
            )
            schedule_future_boot_snapshot_write("qmlearn_audio_stem_index", delay=1.0)
        except Exception as exc:
            stt_debug_log("qmdict_audio_stem_index_write_failed", error=str(exc))
    return stems


def qmdict_local_vietnamese_audio_stem_index(force: bool = False) -> set[str]:
    return set(qmdict_audio_stem_index_shared(force=force))


def qmdict_meaning_has_local_audio_stem(meaning: object, existing_stems: set[str]) -> bool:
    text = clean(meaning)
    if not text:
        return False
    try:
        if str(PROGRAME_ROOT) not in sys.path:
            sys.path.insert(0, str(PROGRAME_ROOT))
        from module_main.Data_Input.local_sound_loader import build_sound_storage_stem  # noqa: PLC0415

        stem = clean(build_sound_storage_stem(text))
    except Exception:
        stem = text
    if not stem:
        return False
    return stem in existing_stems or f"{stem}_vi-VN" in existing_stems or f"{stem}_vi" in existing_stems


VIETNAMESE_STEM_CHAR_RE = re.compile(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", re.I)


def qmdict_audio_stem_is_probably_vietnamese(stem: str) -> bool:
    text = clean(stem)
    if not text:
        return False
    lower = text.lower()
    if lower.endswith(("_en-us", "_en-gb")):
        return False
    if re.search(r"_[a-z]{2}-[a-z]{2}$", lower) and not lower.endswith(("_vi-vn", "_vi")):
        return False
    if lower.endswith(("_vi-vn", "_vi")):
        return True
    if VIETNAMESE_STEM_CHAR_RE.search(text):
        return True
    if any(mark in text for mark in (",", ";", "《", "》")):
        return True
    return False


def cleanup_orphan_qmdict_vietnamese_audio(entries: list[tuple[str, str]]) -> dict:
    try:
        from module_main.Data_Input.local_sound_loader import build_sound_storage_stem, clear_internal_cache  # noqa: PLC0415
    except Exception as exc:
        return {"total": 0, "done": 0, "deleted": 0, "kept": 0, "skipped": 0, "failed": 1, "error": str(exc)}
    root = Path(r"C:\QMLearn\Data")
    try:
        root_resolved = root.resolve()
    except Exception:
        root_resolved = root
    valid_stems: set[str] = set()
    for _key, meaning in entries:
        try:
            stem = build_sound_storage_stem(meaning)
        except Exception:
            stem = clean(meaning)
        if stem:
            valid_stems.add(stem)
    candidates = [path for path in root.glob("*.txt") if qmdict_audio_stem_is_probably_vietnamese(path.stem)]
    total = len(candidates)
    done = deleted = kept = skipped = failed = 0
    deleted_samples: list[str] = []
    with QMDICT_AUDIO_REFRESH_LOCK:
        QMDICT_AUDIO_REFRESH_JOB.update(
            {
                "phase": "cleaning",
                "message": "Deleting orphan Vietnamese audio not present in QmDict.",
                "cleanup_total": total,
                "cleanup_done": 0,
                "cleanup_deleted": 0,
                "updated_at": utc_timestamp(),
            }
        )
        snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
    write_qmdict_audio_refresh_progress({"version": 1, **snapshot})
    for path in candidates:
        done += 1
        try:
            resolved = path.resolve()
            resolved.relative_to(root_resolved)
            stem = path.stem
            base_stem = re.sub(r"_(?:vi-vn|vi)$", "", stem, flags=re.I)
            if stem in valid_stems or base_stem in valid_stems:
                kept += 1
            else:
                path.unlink()
                deleted += 1
                if len(deleted_samples) < 30:
                    deleted_samples.append(path.name)
        except Exception:
            failed += 1
        if done == total or done % 500 == 0:
            with QMDICT_AUDIO_REFRESH_LOCK:
                QMDICT_AUDIO_REFRESH_JOB.update(
                    {
                        "cleanup_done": done,
                        "cleanup_deleted": deleted,
                        "updated_at": utc_timestamp(),
                    }
            )
                snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
            write_qmdict_audio_refresh_progress({"version": 1, **snapshot})
    try:
        clear_internal_cache()
    except Exception:
        pass
    result = {
        "total": total,
        "done": done,
        "deleted": deleted,
        "kept": kept,
        "skipped": skipped,
        "failed": failed,
        "samples": deleted_samples,
    }
    stt_debug_log("qmdict_orphan_vi_audio_cleanup_done", **result)
    return result


def run_qmdict_meaning_audio_refresh_job(job_id: str, keys: object = None, mode: str = "qmdict-missing") -> None:
    downloaded = cached = failed = done = scanned = missing_count = 0
    report_rows: list[dict] = []
    missing_entries: list[tuple[str, str]] = []
    try:
        ensure_qmdict_runtime_fresh(force=True)
        entries = qmdict_audio_refresh_entries(keys)
        scan_total = len(entries)
        existing_audio_stems = qmdict_local_vietnamese_audio_stem_index()
        with QMDICT_AUDIO_REFRESH_LOCK:
            QMDICT_AUDIO_REFRESH_JOB.update(
                {
                    "phase": "scanning",
                    "message": "Comparing QmDict meanings with the local MP3 audio index.",
                    "scan_total": scan_total,
                    "scan_done": 0,
                    "workers": 0,
                    "cleanup_total": 0,
                    "cleanup_done": 0,
                    "cleanup_deleted": 0,
                    "total": 0,
                    "done": 0,
                    "cached": 0,
                    "missing": 0,
                    "downloaded": 0,
                    "failed": 0,
                    "updated_at": utc_timestamp(),
                    "error": "",
                }
            )
            snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
        write_qmdict_audio_refresh_progress({"version": 1, **snapshot})

        for key, meaning in entries:
            scanned += 1
            row = {"key": key, "meaning": meaning, "status": ""}
            try:
                if qmdict_meaning_has_local_audio_stem(meaning, existing_audio_stems):
                    cached += 1
                    row["status"] = "cached-mp3"
                else:
                    missing_entries.append((key, meaning))
                    missing_count += 1
                    row["status"] = "missing-local"
            except Exception as exc:
                missing_entries.append((key, meaning))
                missing_count += 1
                row["status"] = "local-check-failed"
                row["error"] = str(exc)
            if not clean(row["status"]).startswith("cached"):
                report_rows.append(row)
            if scanned == scan_total or scanned % 100 == 0 or ((not clean(row["status"]).startswith("cached")) and missing_count <= 20):
                with QMDICT_AUDIO_REFRESH_LOCK:
                    QMDICT_AUDIO_REFRESH_JOB.update(
                        {
                            "scan_done": scanned,
                            "cached": cached,
                            "missing": missing_count,
                            "last_key": key,
                            "last_meaning": meaning[:180],
                            "updated_at": utc_timestamp(),
                        }
                    )
                    snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
                write_qmdict_audio_refresh_progress({"version": 1, **snapshot})

        cleanup_result = cleanup_orphan_qmdict_vietnamese_audio(entries)

        total = len(missing_entries)
        worker_count = min(QMDICT_AUDIO_REFRESH_MAX_WORKERS, total) if total else 0
        with QMDICT_AUDIO_REFRESH_LOCK:
            QMDICT_AUDIO_REFRESH_JOB.update(
                {
                    "phase": "downloading" if total else "complete",
                    "message": f"Downloading only missing Vietnamese audio with {worker_count} background workers."
                    if total
                    else "All Vietnamese audio is already cached.",
                    "scan_done": scanned,
                    "scan_total": scan_total,
                    "workers": worker_count,
                    "cleanup_total": int(cleanup_result.get("total", 0) or 0),
                    "cleanup_done": int(cleanup_result.get("done", 0) or 0),
                    "cleanup_deleted": int(cleanup_result.get("deleted", 0) or 0),
                    "total": total,
                    "done": 0,
                    "missing": total,
                    "cached": cached,
                    "downloaded": 0,
                    "failed": 0,
                    "updated_at": utc_timestamp(),
                }
            )
            snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
        write_qmdict_audio_refresh_progress({"version": 1, **snapshot})

        def download_missing_meaning(item: tuple[str, str]) -> dict:
            key, meaning = item
            row = {"key": key, "meaning": meaning, "status": ""}
            try:
                # A parallel edit/build may have created the file after the scan.
                local_audio_path = qmdict_meaning_audio_local_path(meaning)
                if local_audio_path is not None:
                    ensure_qmlearn_data_sound_plain_mp3(local_audio_path)
                    row["status"] = "cached-late"
                else:
                    clip = qmdict_space_v_meaning_audio_map(meaning)
                    if clip:
                        row["status"] = "downloaded"
                    else:
                        row["status"] = "missing"
            except Exception as exc:
                row["status"] = "failed"
                row["error"] = str(exc)
            return row

        if missing_entries:
            with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="qmdict-audio") as executor:
                future_map = {executor.submit(download_missing_meaning, item): item for item in missing_entries}
                for future in concurrent.futures.as_completed(future_map):
                    key, meaning = future_map[future]
                    done += 1
                    try:
                        row = future.result()
                    except Exception as exc:
                        row = {"key": key, "meaning": meaning, "status": "failed", "error": str(exc)}
                    status = clean(row.get("status", ""))
                    if status == "cached-late":
                        cached += 1
                    elif status == "downloaded":
                        downloaded += 1
                    else:
                        failed += 1
                    report_rows.append(row)
                    with QMDICT_AUDIO_REFRESH_LOCK:
                        QMDICT_AUDIO_REFRESH_JOB.update(
                            {
                                "done": done,
                                "cached": cached,
                                "downloaded": downloaded,
                                "failed": failed,
                                "last_key": key,
                                "last_meaning": meaning[:180],
                                "updated_at": utc_timestamp(),
                            }
                        )
                        snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
                    if done == total or done % 10 == 0 or status in {"failed", "missing"}:
                        write_qmdict_audio_refresh_progress({"version": 1, **snapshot})
        if downloaded > 0:
            qmdict_local_vietnamese_audio_stem_index(force=True)
        completed_at = utc_timestamp()
        with QMDICT_AUDIO_REFRESH_LOCK:
            QMDICT_AUDIO_REFRESH_JOB.update(
                {
                    "running": False,
                    "phase": "complete",
                    "message": "Vietnamese audio refresh complete.",
                    "completed_at": completed_at,
                    "updated_at": completed_at,
                }
            )
            final_snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
        atomic_write_json(
            QMDICT_AUDIO_REFRESH_REPORT_FILE,
            {"version": 1, **final_snapshot, "items": report_rows[-1000:]},
            indent=2,
        )
        write_qmdict_audio_refresh_progress({"version": 1, **final_snapshot})
        stt_debug_log(
            "qmdict_audio_refresh_done",
            job_id=job_id,
            mode=mode,
            scanned=scanned,
            missing=total,
            cached=cached,
            downloaded=downloaded,
            failed=failed,
        )
    except Exception as exc:
        with QMDICT_AUDIO_REFRESH_LOCK:
            QMDICT_AUDIO_REFRESH_JOB.update(
                {
                    "running": False,
                    "phase": "failed",
                    "message": "Vietnamese audio refresh failed.",
                    "updated_at": utc_timestamp(),
                    "error": str(exc),
                }
            )
            snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
        write_qmdict_audio_refresh_progress({"version": 1, **snapshot})
        stt_debug_log("qmdict_audio_refresh_failed", job_id=job_id, mode=mode, error=str(exc))


def start_qmdict_meaning_audio_refresh(keys: object = None, mode: str = "qmdict-missing") -> dict:
    with QMDICT_AUDIO_REFRESH_LOCK:
        if QMDICT_AUDIO_REFRESH_JOB.get("running"):
            return {"started": False, "audio_refresh": dict(QMDICT_AUDIO_REFRESH_JOB)}
        job_id = uuid.uuid4().hex
        started_at = utc_timestamp()
        QMDICT_AUDIO_REFRESH_JOB.update(
            {
                "running": True,
                "job_id": job_id,
                "mode": mode,
                "phase": "queued",
                "message": "Waiting to scan local Vietnamese audio.",
                "started_at": started_at,
                "updated_at": started_at,
                "completed_at": "",
                "scan_total": 0,
                "scan_done": 0,
                "workers": 0,
                "cleanup_total": 0,
                "cleanup_done": 0,
                "cleanup_deleted": 0,
                "total": 0,
                "done": 0,
                "cached": 0,
                "missing": 0,
                "downloaded": 0,
                "failed": 0,
                "last_key": "",
                "last_meaning": "",
                "error": "",
            }
        )
        snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
    thread = threading.Thread(
        target=run_qmdict_meaning_audio_refresh_job,
        args=(job_id, keys, mode),
        name=f"qmdict-audio-refresh-{job_id[:8]}",
        daemon=True,
    )
    thread.start()
    write_qmdict_audio_refresh_progress({"version": 1, **snapshot})
    return {"started": True, "audio_refresh": snapshot}


def start_qmdict_meaning_audio_refresh_deferred(keys: object = None, mode: str = "qmdict-missing", delay_seconds: float = 0.4) -> dict:
    with QMDICT_AUDIO_REFRESH_LOCK:
        if QMDICT_AUDIO_REFRESH_JOB.get("running"):
            return {"scheduled": False, "started": False, "audio_refresh": dict(QMDICT_AUDIO_REFRESH_JOB)}
    delay = max(0.0, float(delay_seconds or 0.0))

    def _worker() -> None:
        if delay > 0:
            time.sleep(delay)
        try:
            start_qmdict_meaning_audio_refresh(keys=keys, mode=mode)
        except Exception as exc:
            stt_debug_log("qmdict_audio_deferred_start_failed", mode=mode, error=str(exc))

    threading.Thread(
        target=_worker,
        name=f"qmdict-audio-deferred-{uuid.uuid4().hex[:8]}",
        daemon=True,
    ).start()
    snapshot = qmdict_audio_refresh_job_snapshot()
    return {"scheduled": True, "started": False, "delay_seconds": delay, "audio_refresh": snapshot}


def schedule_qmdict_meaning_audio_refresh(meaning: object = "") -> None:
    text = clean(meaning)
    if not text:
        return
    key = hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()
    with QMDICT_AUDIO_REFRESH_LOCK:
        if key in QMDICT_AUDIO_REFRESH_INFLIGHT:
            return
        QMDICT_AUDIO_REFRESH_INFLIGHT.add(key)

    def worker() -> None:
        try:
            if qmdict_meaning_audio_local_path(text) is None:
                qmdict_space_v_meaning_audio_map(text)
        finally:
            with QMDICT_AUDIO_REFRESH_LOCK:
                QMDICT_AUDIO_REFRESH_INFLIGHT.discard(key)

    threading.Thread(target=worker, name=f"qmdict-meaning-audio-{key[:8]}", daemon=True).start()


def space_v_word_value(row: object, field: str) -> object:
    if isinstance(row, dict):
        compact_keys = {"word": "w", "meaning": "m", "pron": "p", "type": "ty", "audio": "au"}
        long_keys = {"word": "word", "meaning": "meaning", "pron": "pron", "type": "type", "audio": "audio"}
        key = compact_keys.get(field) if any(k in row for k in ("w", "m", "ty", "au")) else long_keys.get(field)
        return row.get(key, "") if key else ""
    if isinstance(row, list):
        indexes = {"word": 0, "meaning": 1, "pron": 2, "type": 3, "audio": 4}
        index = indexes.get(field, -1)
        return row[index] if 0 <= index < len(row) else ({} if field == "audio" else "")
    return {} if field == "audio" else ""


def set_space_v_word_value(row: object, field: str, value: object) -> None:
    if isinstance(row, dict):
        compact = any(k in row for k in ("w", "m", "ty", "au"))
        keys = {"word": "w", "meaning": "m", "pron": "p", "type": "ty", "audio": "au"} if compact else {"word": "word", "meaning": "meaning", "pron": "pron", "type": "type", "audio": "audio"}
        key = keys.get(field)
        if key:
            row[key] = value
        return
    if isinstance(row, list):
        indexes = {"word": 0, "meaning": 1, "pron": 2, "type": 3, "audio": 4}
        index = indexes.get(field, -1)
        if index < 0:
            return
        while len(row) <= index:
            row.append({} if len(row) == 4 else "")
        row[index] = value


def qmdict_lookup_summary_space_v_fast(word: object = "", surface: str = "") -> dict:
    # Added 2026-07-06: Space_V opens use warmed QmDict summary maps before falling back to worker lookups.
    text = clean(word)
    if not text:
        return {}
    signature_key = qmdict_source_signature_key()
    lookup_cache_key = (signature_key, pdf_vocab_word_key(text) or vocab_key(text))
    with QMDICT_LOOKUP_SUMMARY_CACHE_LOCK:
        cached = QMDICT_LOOKUP_SUMMARY_CACHE.get(lookup_cache_key)
        if isinstance(cached, dict):
            out = dict(cached)
            if out:
                out["surface"] = clean(surface) or clean(out.get("surface", "")) or text
            return out
    with QMDICT_SUMMARY_MAP_CACHE_LOCK:
        cached_signature = QMDICT_SUMMARY_MAP_CACHE.get("signature")
        cached_maps = QMDICT_SUMMARY_MAP_CACHE.get("maps")
        if cached_signature == signature_key and isinstance(cached_maps, dict) and cached_maps:
            summary = cached_maps.get(vocab_key(text)) or cached_maps.get(pdf_vocab_word_key(text))
            if isinstance(summary, dict) and summary:
                stored = dict(summary)
                stored["surface"] = ""
                with QMDICT_LOOKUP_SUMMARY_CACHE_LOCK:
                    QMDICT_LOOKUP_SUMMARY_CACHE[lookup_cache_key] = stored
                    if len(QMDICT_LOOKUP_SUMMARY_CACHE) > QMDICT_LOOKUP_SUMMARY_CACHE_LIMIT:
                        QMDICT_LOOKUP_SUMMARY_CACHE.clear()
                out = dict(stored)
                out["surface"] = clean(surface) or text
                return out
    return qmdict_lookup_summary_queued(text, surface)


def minimal_space_v_word_row(row: object) -> dict | None:
    word = clean(space_v_word_value(row, "word"))
    if not word:
        return None
    summary = qmdict_lookup_summary_space_v_fast(word)
    if not summary:
        return None
    next_word = clean(summary.get("word", "")) or word
    return {"w": next_word}


def hydrated_space_v_word_row(row: object) -> dict | None:
    word = clean(space_v_word_value(row, "word"))
    if not word:
        return None
    summary = qmdict_lookup_summary_space_v_fast(word)
    if not summary:
        return None
    next_word = clean(summary.get("word", "")) or word
    meaning = clean(summary.get("meaning", ""))
    if not meaning:
        return None
    pron = clean(summary.get("pron", ""))
    word_type = clean(summary.get("type", ""))
    return {
        "w": next_word,
        "m": meaning,
        "p": pron,
        "ty": word_type,
        "au": qmdict_space_v_dynamic_audio_map(next_word, meaning),
        "d": qmdict_space_v_dynamic_detail(next_word, summary),
        "im": qmdict_space_v_cached_image(next_word),
    }


def hydrate_space_v_payload_with_qmdict(payload: dict) -> tuple[dict, dict]:
    if not isinstance(payload, dict):
        return {}, {"hydrated": 0, "removed": 0}
    source_key = "w" if isinstance(payload.get("w"), list) else "words" if isinstance(payload.get("words"), list) else ""
    rows = payload.get(source_key) if source_key else []
    next_rows: list[dict] = []
    removed = 0
    for row in rows if isinstance(rows, list) else []:
        hydrated = hydrated_space_v_word_row(row)
        if hydrated:
            next_rows.append(hydrated)
        else:
            removed += 1
    next_payload = dict(payload)
    if source_key:
        next_payload[source_key] = next_rows
    elif payload.get("k") == "ftv":
        next_payload["w"] = next_rows
    else:
        next_payload["words"] = next_rows
    next_payload["dyn"] = {"qmdict": True, "hydrated": len(next_rows), "removed": removed}
    return next_payload, {"hydrated": len(next_rows), "removed": removed}


def minimize_space_v_payload_with_qmdict(payload: dict) -> tuple[dict, dict]:
    if not isinstance(payload, dict):
        return {}, {"changed": 0, "removed": 0, "kept": 0}
    source_key = "w" if isinstance(payload.get("w"), list) else "words" if isinstance(payload.get("words"), list) else ""
    rows = payload.get(source_key) if source_key else []
    next_rows: list[dict] = []
    seen: set[str] = set()
    removed = 0
    for row in rows if isinstance(rows, list) else []:
        minimal = minimal_space_v_word_row(row)
        key = vocab_key(minimal.get("w", "")) if minimal else ""
        if minimal and key and key not in seen:
            seen.add(key)
            next_rows.append(minimal)
        else:
            removed += 1
    keep_keys = {"k", "v", "t", "title", "created", "batch", "b", "voices", "vc", "fx", "effects", "mission", "ms", "kind", "version", "st", "study"}
    next_payload = {key: value for key, value in payload.items() if key in keep_keys}
    if payload.get("k") == "ftv" or source_key == "w":
        next_payload.setdefault("k", "ftv")
        next_payload.setdefault("v", payload.get("v", 1) or 1)
        next_payload["w"] = next_rows
    else:
        next_payload.setdefault("kind", "future_vocabulary_payload")
        next_payload["words"] = next_rows
    changed = 1 if next_payload != payload else 0
    return next_payload, {"changed": changed, "removed": removed, "kept": len(next_rows)}


def sync_space_v_file_with_qmdict(target: Path) -> dict:
    target = Path(target)
    if target.suffix.lower() != ".space_v" or not target.is_file():
        return {"changed": 0, "audio_changed": 0, "removed": 0}
    with SPACE_V_QMDICT_SYNC_LOCK:
        try:
            payload, structure_path = load_future_lesson_document(target)
        except Exception as exc:
            stt_debug_log("space_v_qmdict_sync_decode_failed", path=str(target), error=str(exc))
            return {"changed": 0, "audio_changed": 0, "removed": 0, "error": str(exc)}
        rows = payload.get("w") if isinstance(payload.get("w"), list) else payload.get("words")
        if not isinstance(rows, list) or not rows:
            return {"changed": 0, "audio_changed": 0, "removed": 0}
        next_payload, result = minimize_space_v_payload_with_qmdict(payload)
        changed = int(result.get("changed", 0) or 0)
        removed = int(result.get("removed", 0) or 0)
        if changed:
            backup_lesson_file_before_study_repair(target, structure_path)
            write_future_lesson_document(target, next_payload, structure_path)
            try:
                with SERVER_DATA_FILE_CACHE_LOCK:
                    SERVER_DATA_FILE_CACHE.pop(server_data_file_cache_key(target), None)
            except Exception:
                pass
            stt_debug_log("space_v_qmdict_minimize_done", path=server_data_relative(target), changed=changed, removed=removed, kept=result.get("kept", 0))
        return {"changed": changed, "audio_changed": 0, "removed": removed, "kept": result.get("kept", 0)}


def minimal_space_v_payload_from_entries(
    entries: object,
    title: str = "Vocabulary",
    batch_index: int = 1,
    batch_total: int = 1,
    mission: dict | None = None,
) -> dict:
    rows: list[dict] = []
    seen: set[str] = set()
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, dict):
            word = clean(entry.get("word") or entry.get("w") or entry.get("en") or entry.get("e") or "")
        else:
            word = clean(getattr(entry, "word", ""))
        minimal = minimal_space_v_word_row({"w": word}) if word else None
        key = vocab_key(minimal.get("w", "")) if minimal else ""
        if minimal and key and key not in seen:
            seen.add(key)
            rows.append(minimal)
    payload = {
        "k": "ftv",
        "v": 1,
        "t": clean(title) or "Vocabulary",
        "created": int(time.time()),
        "batch": {
            "i": max(1, int(batch_index or 1)),
            "total": max(1, int(batch_total or 1)),
            "size": len(rows),
        },
        "voices": [
            {"label": "Sound of Text | Female UK", "key": "sot:en-GB"},
            {"label": "Sound of Text | Female US", "key": "sot:en-US"},
        ],
        "w": rows,
    }
    if isinstance(mission, dict) and mission:
        payload["mission"] = mission
    return payload


# Added 2026-07-22: every runtime-generated Space_V reserves and embeds its canonical ID before publication.
def write_generated_space_v_lesson(target: Path, payload: dict) -> str:
    from future_lesson_identity import (
        apply_lesson_id_to_payload,
        ensure_future_lesson_id,
        lesson_id_from_payload,
    )

    output = Path(target)
    if output.is_file() and not lesson_id_from_payload(payload):
        try:
            existing_payload, _structure_path = load_future_lesson_document(output)
            existing_id = lesson_id_from_payload(existing_payload)
            if existing_id:
                apply_lesson_id_to_payload(payload, existing_id)
        except Exception as exc:
            raise RuntimeError(f"Cannot preserve the existing Space_V identity for {output.name}: {exc}") from exc
    lesson_id = ensure_future_lesson_id(payload, output_path=output, space="Space_V")
    atomic_write_text(output, encode_future_payload_code(payload) + "\n", encoding="utf-8")
    return lesson_id


def space_v_qmdict_repair_snapshot() -> dict:
    with SPACE_V_QMDICT_REPAIR_LOCK:
        return dict(SPACE_V_QMDICT_REPAIR_JOB)


def iter_server_space_v_files() -> list[Path]:
    root = SERVER_DATA_ROOT.resolve()
    files: list[Path] = []
    try:
        for item in root.rglob("*"):
            try:
                if item.is_file() and item.suffix.lower() == ".space_v":
                    files.append(item)
            except OSError:
                continue
    except Exception:
        return files
    return sorted(files, key=lambda path: str(path).lower())


def run_space_v_qmdict_repair_job(job_id: str) -> None:
    changed = audio_changed = removed = failed = 0
    try:
        files = iter_server_space_v_files()
        total = len(files)
        with SPACE_V_QMDICT_REPAIR_LOCK:
            SPACE_V_QMDICT_REPAIR_JOB.update(
                {
                    "running": True,
                    "job_id": job_id,
                    "updated_at": utc_timestamp(),
                    "total": total,
                    "done": 0,
                    "changed": 0,
                    "audio_changed": 0,
                    "removed": 0,
                    "failed": 0,
                    "last": "",
                    "error": "",
                }
            )
        for index, target in enumerate(files, 1):
            rel = server_data_relative(target)
            try:
                result = sync_space_v_file_with_qmdict(target)
                changed += int(result.get("changed", 0) or 0)
                audio_changed += int(result.get("audio_changed", 0) or 0)
                removed += int(result.get("removed", 0) or 0)
            except Exception as exc:
                failed += 1
                stt_debug_log("space_v_qmdict_repair_file_failed", path=rel, error=str(exc))
            if index == total or index % 5 == 0:
                with SPACE_V_QMDICT_REPAIR_LOCK:
                    SPACE_V_QMDICT_REPAIR_JOB.update(
                        {
                            "updated_at": utc_timestamp(),
                            "done": index,
                            "changed": changed,
                            "audio_changed": audio_changed,
                            "removed": removed,
                            "failed": failed,
                            "last": rel,
                        }
                    )
        with SPACE_V_QMDICT_REPAIR_LOCK:
            SPACE_V_QMDICT_REPAIR_JOB.update(
                {
                    "running": False,
                    "updated_at": utc_timestamp(),
                    "completed_at": utc_timestamp(),
                    "done": total,
                    "changed": changed,
                    "audio_changed": audio_changed,
                    "removed": removed,
                    "failed": failed,
                    "last": files[-1].name if files else "",
                    "error": "",
                }
            )
        stt_debug_log("space_v_qmdict_repair_done", total=total, changed=changed, audio_changed=audio_changed, removed=removed, failed=failed)
    except Exception as exc:
        with SPACE_V_QMDICT_REPAIR_LOCK:
            SPACE_V_QMDICT_REPAIR_JOB.update({"running": False, "updated_at": utc_timestamp(), "completed_at": utc_timestamp(), "error": str(exc)})
        stt_debug_log("space_v_qmdict_repair_failed", error=str(exc))


def start_space_v_qmdict_repair() -> dict:
    with SPACE_V_QMDICT_REPAIR_LOCK:
        if SPACE_V_QMDICT_REPAIR_JOB.get("running"):
            return {"started": False, "repair": dict(SPACE_V_QMDICT_REPAIR_JOB)}
        job_id = uuid.uuid4().hex
        now = utc_timestamp()
        SPACE_V_QMDICT_REPAIR_JOB.update(
            {
                "running": True,
                "job_id": job_id,
                "started_at": now,
                "updated_at": now,
                "completed_at": "",
                "total": 0,
                "done": 0,
                "changed": 0,
                "audio_changed": 0,
                "removed": 0,
                "failed": 0,
                "last": "",
                "error": "",
            }
        )
        snapshot = dict(SPACE_V_QMDICT_REPAIR_JOB)
    threading.Thread(target=run_space_v_qmdict_repair_job, args=(job_id,), daemon=True, name=f"space-v-repair-{job_id[:8]}").start()
    return {"started": True, "repair": snapshot}
