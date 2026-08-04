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


# Added 2026-07-31: share the same cancellable session contract with English audio refresh.
def qmdict_audio_refresh_cancel_requested(job_id: object = "") -> bool:
    with QMDICT_AUDIO_REFRESH_LOCK:
        return bool(
            QMDICT_AUDIO_REFRESH_JOB.get("running")
            and clean(QMDICT_AUDIO_REFRESH_JOB.get("job_id")) == clean(job_id)
            and QMDICT_AUDIO_REFRESH_JOB.get("cancel_requested")
        )


def qmdict_word_audio_refresh_job_snapshot() -> dict:
    with QMDICT_WORD_AUDIO_REFRESH_LOCK:
        return dict(QMDICT_WORD_AUDIO_REFRESH_JOB)


# Added 2026-07-31: let dashboard shutdown cancel queued refresh work before the server exits.
def qmdict_word_audio_refresh_cancel_requested(job_id: object = "") -> bool:
    with QMDICT_WORD_AUDIO_REFRESH_LOCK:
        return bool(
            QMDICT_WORD_AUDIO_REFRESH_JOB.get("running")
            and clean(QMDICT_WORD_AUDIO_REFRESH_JOB.get("job_id")) == clean(job_id)
            and QMDICT_WORD_AUDIO_REFRESH_JOB.get("cancel_requested")
        )


# Added 2026-07-31: fail before queue creation when the lightweight audio runtime is unavailable.
def verify_qmdict_word_audio_runtime() -> None:
    try:
        from module_main.Soundoftext_Api import Soundoftext_Api  # noqa: F401, PLC0415
        from module_main.Data_Input.local_sound_loader import build_sound_file_name  # noqa: F401, PLC0415
    except Exception as exc:
        raise RuntimeError(f"QmDict audio runtime is not ready: {exc}") from exc
    try:
        QMLEARN_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        probe = QMLEARN_DATA_ROOT / f".future_qmdict_audio_preflight_{os.getpid()}.tmp"
        probe.write_bytes(b"preflight")
        probe.unlink(missing_ok=True)
    except Exception as exc:
        raise RuntimeError(f"QmDict audio folder is not writable: {exc}") from exc


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


# Added 2026-07-31: QmDict stores many headwords in all caps; title-case them before TTS
# so Sound of Text speaks the word instead of treating it as an acronym.
def normalize_qmdict_tts_word(text: object = "") -> str:
    value = clean(text)
    if value and any(char.isalpha() for char in value) and value == value.upper():
        lowered = value.lower()
        for index, char in enumerate(lowered):
            if char.isalpha():
                return lowered[:index] + char.upper() + lowered[index + 1:]
    return value


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


# Added 2026-07-31: bulk audio balances across all workers, then falls back per item on Server 2.
def synthesize_bulk_audio_worker_first(text: object = "", voice_key: object = "", log=None) -> tuple[bytes, str]:
    target_text = clean(text)
    target_voice = clean(voice_key)
    worker_voice = target_voice
    if not worker_voice.lower().startswith(("sot:", "soundoftext:", "edge:", "kokoro:", "kokoro_vi:")):
        normalized_voice = normalize_qmlearn_audio_voice_key(worker_voice)
        if normalized_voice:
            worker_voice = f"sot:{normalized_voice}"
    worker_result = None
    try:
        worker_result = distributed_worker_try_tts_raw(
            target_text,
            worker_voice,
            timeout_seconds=45.0,
            preferred_user="",
            # Interactive learner audio is P1 and builder work is P3.
            priority=2,
        )
    except Exception as exc:
        if callable(log):
            log(f"Distributed worker failed: {exc}")
    audio_bytes = worker_result.get("audio_bytes") if isinstance(worker_result, dict) else None
    if isinstance(audio_bytes, (bytes, bytearray)) and audio_bytes:
        return bytes(audio_bytes), "distributed_worker"
    if callable(log):
        log("No worker audio; falling back to Server 2.")
    return synthesize_space_v_sound_of_text_bytes(target_text, target_voice, log), "server_fallback"


# Added 2026-07-31: keep enough submissions in flight to fill every live TTS worker slot.
def qmdict_bulk_audio_concurrency(remaining: object = 0) -> int:
    total = max(0, int(remaining or 0))
    if total <= 0:
        return 0
    try:
        live_capacity = max(1, int(distributed_worker_effective_job_limit("tts") or 0))
    except Exception:
        live_capacity = max(QMDICT_WORD_AUDIO_REFRESH_MAX_WORKERS, QMDICT_AUDIO_REFRESH_MAX_WORKERS)
    # The synthesis call includes LAN submit/claim and result wait. A window
    # equal to capacity can under-fill workers when those calls are waking up
    # at different times, so keep one bounded prefetch window behind the live
    # capacity. The broker still enforces the per-worker slot limits.
    return min(128, total, max(live_capacity, live_capacity * 2))

def force_save_space_v_sound_audio(text: object = "", voice_key: object = "", audio_bytes: bytes | None = None, log=None) -> Path | None:
    target_text = clean(text)
    target_voice = normalize_qmlearn_audio_voice_key(voice_key) or "en-GB"
    if not target_text or not audio_bytes:
        return None
    try:
        from module_main.Data_Input.local_sound_loader import build_sound_file_name, clear_internal_cache  # noqa: PLC0415
    except Exception as exc:
        if callable(log):
            log(f"Skip QMLearn/Data save {target_text}: {exc}")
        return None
    voice_dir = qmlearn_audio_voice_dir(f"sot:{target_voice}")
    voice_dir.mkdir(parents=True, exist_ok=True)
    target = voice_dir / build_sound_file_name(target_text, target_voice, extension=".mp3")
    temp_target = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp_target.write_bytes(bytes(audio_bytes))
        if temp_target.stat().st_size <= 0:
            raise RuntimeError("Generated audio file is empty.")
        os.replace(temp_target, target)
        clear_internal_cache()
    except Exception as exc:
        try:
            temp_target.unlink(missing_ok=True)
        except Exception:
            pass
        if callable(log):
            log(f"Skip QMLearn/Data save {target_text}: {exc}")
        return None
    candidate = target
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
    # Fallback-only directory index for legacy files missing from the persisted
    # logical asset index. Normal startup does not build this map.
    index: dict[str, Path] = {}
    revisions: dict[str, str] = {}
    try:
        with os.scandir(root_path) as entries:
            for entry in entries:
                try:
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    suffix = Path(entry.name).suffix.lower()
                    if suffix not in {".mp3", ".txt"}:
                        continue
                    path = Path(entry.path)
                    index[entry.name.lower()] = path
                    stat = entry.stat(follow_symlinks=False)
                    revisions[entry.name.lower()] = f"{int(stat.st_mtime_ns):x}-{int(stat.st_size):x}"
                except OSError:
                    continue
    except OSError:
        index = {}
        revisions = {}
    with QMLEARN_AUDIO_DIR_INDEX_LOCK:
        QMLEARN_AUDIO_DIR_INDEX[key] = index
        QMLEARN_AUDIO_DIR_REVISION_INDEX[key] = revisions
    return index


# Added 2026-07-31: audio paths are deterministic; startup records only the
# cheap QmDict signature and never loads or rebuilds a full audio registry.
def warm_qmlearn_voice_audio_index_async(delay_seconds: float = 0.0) -> None:
    def _worker() -> None:
        try:
            if delay_seconds and delay_seconds > 0:
                time.sleep(min(10.0, max(0.0, float(delay_seconds or 0.0))))
            started = time.perf_counter()
            signature = qmdict_source_signature_key()
            SERVER_STATE["qmlearn_voice_index_ready"] = True
            SERVER_STATE["qmlearn_voice_index_warmed"] = {
                "assets": 0,
                "qmdict_signature": list(signature),
                "directory_scanned": False,
            }
            SERVER_STATE["qmlearn_voice_index_ms"] = int((time.perf_counter() - started) * 1000)
            SERVER_STATE["qmlearn_audio_index_mode"] = "deterministic-exact-path"
            stt_debug_log(
                "qmlearn_voice_audio_index_warm_done",
                qmdict_signature=signature,
                directory_scanned=False,
                elapsed_ms=SERVER_STATE["qmlearn_voice_index_ms"],
            )
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
    revision = qmlearn_audio_file_revision(audio_path)
    accent_key = "u" if target_voice.lower().endswith("en-us") else "g"
    asset = {
        "path": audio_path,
        "revision": revision or "missing",
        "asset_id": f"v2:w:{vocab_key(target_text)}:{accent_key}:{revision or 'missing'}",
    }
    sound_url = qmlearn_sound_url_for_audio_path(audio_path, f"/server-data/qm-sound?path={quote(rel_path, safe='')}")
    return {
        "audio_path": sound_url,
        "audio": {"path": sound_url, "mime": "audio/mpeg", "voice": target_voice, "asset_id": clean(asset.get("asset_id")), "cached": True},
        "audio_mime": "audio/mpeg",
        "asset_id": clean(asset.get("asset_id")),
        "revision": clean(asset.get("revision")),
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
    voice_dir = qmlearn_audio_voice_dir(voice_key)
    roots = [voice_dir]
    normalized_voice = normalize_qmlearn_audio_voice_key(voice_key).lower()
    # Added 2026-07-31: English SOT assets are canonical only in their accent
    # folder; the Data root contains legacy/broken clips and must not win.
    if voice_dir != QMLEARN_DATA_ROOT and normalized_voice not in {"en-gb", "en-us"}:
        roots.append(QMLEARN_DATA_ROOT)
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
    # Added 2026-07-31: do not materialize the persisted asset map for a cold
    # learner request. Startup warms directory indexes in the background; until
    # then, the exact asset index and direct candidates are sufficient and avoid
    # copying a large 95k-entry map while opening Space_V.
    if found is None and use_index and allow_scan:
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


# Added 2026-07-30: cache one content revision per resolved QMLearn audio file so clients invalidate only changed words.
def qmlearn_audio_file_revision(audio_path: object = None) -> str:
    try:
        target = Path(audio_path).resolve()
        target.relative_to(QMLEARN_DATA_ROOT.resolve())
        cache_key = str(target).lower()
        stat = target.stat()
        mtime_ns = int(stat.st_mtime_ns)
        size = int(stat.st_size)
    except Exception:
        return ""
    with QMLEARN_AUDIO_REVISION_CACHE_LOCK:
        cached = QMLEARN_AUDIO_REVISION_CACHE.get(cache_key)
        if cached and cached[0] == mtime_ns and cached[1] == size:
            return cached[2]
        revision = f"{mtime_ns:x}-{size:x}"
        QMLEARN_AUDIO_REVISION_CACHE[cache_key] = (mtime_ns, size, revision)
        if len(QMLEARN_AUDIO_REVISION_CACHE) > 24000:
            for key in list(QMLEARN_AUDIO_REVISION_CACHE.keys())[:6000]:
                QMLEARN_AUDIO_REVISION_CACHE.pop(key, None)
        return revision


def qmlearn_word_audio_asset(word: object = "", voice_key: object = "") -> dict:
    target_word = clean(word)
    target_voice = normalize_space_v_refresh_voice(voice_key)
    # Shared by Space V/W, PDF/Picture, QM City and direct qm-sound requests.
    # The shared resolver must never block a learner on a full folder scan.
    audio_path = fast_qmlearn_audio_path(target_word, target_voice, allow_scan=False, use_index=True)
    revision = qmlearn_audio_file_revision(audio_path) if audio_path else ""
    accent_key = "u" if target_voice.lower().endswith("en-us") else "g"
    base_asset_id = f"v2:w:{vocab_key(target_word)}:{accent_key}"
    return {
        "path": audio_path,
        "revision": revision or "missing",
        "asset_id": f"{base_asset_id}:{revision or 'missing'}",
        "voice": target_voice,
    }


# Added 2026-07-30: meaning clips share the same revisioned identity contract
# as English word clips instead of a permanent text-only cache key.
def qmlearn_meaning_audio_asset(meaning: object = "") -> dict:
    text = clean(meaning)
    path = qmdict_meaning_audio_local_path(text) if text else None
    revision = qmlearn_audio_file_revision(path) if path else ""
    digest = hashlib.sha256(text.lower().encode("utf-8")).hexdigest()[:32] if text else ""
    return {
        "path": path,
        "revision": revision or "missing",
        "asset_id": f"v2:m:{digest}:{revision or 'missing'}" if digest else "",
    }


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


def refresh_qmlearn_audio_dir_index_entry(text: object = "", voice_key: object = "") -> None:
    """Update one warm voice-directory index entry without rescanning all audio."""
    target_text = clean(text)
    target_voice = clean(voice_key) or "sot:en-GB"
    if not target_text:
        return
    voice_dir = qmlearn_audio_voice_dir(target_voice)
    try:
        voice_key_text = str(voice_dir.resolve()).lower()
    except Exception:
        return
    target = None
    for path in qmlearn_audio_direct_candidates(target_text, target_voice):
        try:
            if str(path.parent.resolve()).lower() == voice_key_text and path.is_file():
                target = path.resolve()
                break
        except Exception:
            continue
    if target is None:
        return
    try:
        stat = target.stat()
        revision = f"{int(stat.st_mtime_ns):x}-{int(stat.st_size):x}"
    except Exception:
        revision = ""
    with QMLEARN_AUDIO_DIR_INDEX_LOCK:
        index = QMLEARN_AUDIO_DIR_INDEX.setdefault(voice_key_text, {})
        index[target.name.lower()] = target
        revisions = QMLEARN_AUDIO_DIR_REVISION_INDEX.setdefault(voice_key_text, {})
        if revision:
            revisions[target.name.lower()] = revision


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
                cache_key = str(candidate.resolve()).lower()
                with QMLEARN_AUDIO_REVISION_CACHE_LOCK:
                    QMLEARN_AUDIO_REVISION_CACHE.pop(cache_key, None)
            except Exception:
                pass
    # Directory indexes are repair-only. A worker write updates only the exact
    # RAM path/revision entries used by learner audio requests.


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
    if audio_path:
        asset = {"path": audio_path, "revision": qmlearn_audio_file_revision(audio_path) or "missing"}
        accent_key = "u" if target_voice.lower().endswith("en-us") else "g"
        asset["asset_id"] = f"v2:w:{vocab_key(target_word)}:{accent_key}:{asset['revision']}"
    else:
        asset = qmlearn_word_audio_asset(target_word, target_voice)
    version = clean(asset.get("revision")) or "missing"
    if rel_path:
        clip = {
            "m": "audio/mpeg",
            "u": qm_sound_protocol_url(rel_path=rel_path, file_revision=version),
            "aid": clean(asset.get("asset_id")),
            "src": "QMLearn/Data/refreshed",
            "voice": target_voice,
        }
    else:
        clip = {
            "m": "audio/mpeg",
            "u": qm_sound_protocol_url(word=target_word, voice=target_voice, file_revision=version),
            "aid": clean(asset.get("asset_id")),
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
    target_word = normalize_qmdict_tts_word(word)
    target_voice = normalize_space_v_refresh_voice(voice_key)
    if not actor:
        raise RuntimeError("Chua dang nhap.")
    if not target_word:
        raise RuntimeError("Thieu tu vung can sua audio.")
    singleflight_wait = wait_for_space_v_audio_refresh_singleflight(target_word, target_voice)
    if singleflight_wait:
        if singleflight_wait.get("timeout"):
            audio_path = fast_qmlearn_audio_path(target_word, target_voice, allow_scan=False, use_index=False)
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
        audio_bytes, audio_source = synthesize_bulk_audio_worker_first(
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
        refresh_qmlearn_audio_dir_index_entry(target_word, target_voice)
    except Exception as exc:
        release_space_v_audio_refresh_quota(actor, day_key, admin=admin)
        finish_space_v_audio_refresh_singleflight(target_word, target_voice, error=f"Khong sua duoc audio Space_V: {exc}")
        raise RuntimeError(f"Khong sua duoc audio Space_V: {exc}") from exc
    finally:
        release_space_v_audio_refresh_slot()
    try:
        invalidate_qmlearn_audio_path_cache(target_word, target_voice)
        invalidated_payloads = invalidate_space_v_audio_payload_cache_for_word(target_word)
        audio_path = saved_path if saved_path and Path(saved_path).is_file() else fast_qmlearn_audio_path(target_word, target_voice, allow_scan=False, use_index=False)
        result = space_v_audio_refresh_result_payload(
            target_word,
            target_voice,
            audio_path,
            invalidated_payloads=invalidated_payloads,
            quota={"limit": daily_limit, "remaining": remaining, "admin": bool(admin), "day": day_key},
        )
        result["source"] = audio_source
        finish_space_v_audio_refresh_singleflight(target_word, target_voice, result=result)
        return result
    except Exception as exc:
        finish_space_v_audio_refresh_singleflight(target_word, target_voice, error=str(exc))
        raise


def qmdict_ocr_audio_priority_words(progress=None, cancelled=None, force: bool = False) -> list[str]:
    """Load the persisted OCR-first order; build it only on the first explicit refresh."""
    try:
        if not force:
            try:
                saved = json.loads(QMDICT_OCR_AUDIO_PRIORITY_FILE.read_text(encoding="utf-8-sig", errors="replace"))
                saved_words = saved.get("words") if isinstance(saved, dict) else None
                if isinstance(saved_words, list):
                    words = [clean(word) for word in saved_words if clean(word)]
                    if callable(progress):
                        progress(int(saved.get("pages", 0) or 0), int(saved.get("pages", 0) or 0), len(words))
                    return words
            except Exception:
                pass
            # The persisted list is intentionally opt-in; normal refreshes never rescan OCR.
            return []
        ocr_revision = int(ocr_cache_revision_ns() or 0)
        qmdict_revision = qmdict_source_signature_key()
        signature = (ocr_revision, qmdict_revision)
        with QMDICT_OCR_AUDIO_PRIORITY_LOCK:
            cached = QMDICT_OCR_AUDIO_PRIORITY_CACHE
            if not force and cached.get("signature") == signature and isinstance(cached.get("words"), list):
                if callable(progress):
                    progress(int(cached.get("pages", 0) or 0), int(cached.get("pages", 0) or 0), len(cached.get("words", [])))
                return list(cached.get("words", []))
        _revision, texts = ocr_cache_text_snapshot()
        _runtime, qmdict = qmdict_runtime_and_dict()
        if not isinstance(qmdict, dict) or not qmdict:
            return []
        lookup: dict[str, str] = {}
        for raw_word in qmdict.keys():
            word = clean(raw_word)
            key = pdf_vocab_word_key(word)
            if word and key and key not in lookup:
                lookup[key] = word
        try:
            viewer_vocab_runtime = qmdict_runtime_module()
        except Exception as exc:
            stt_debug_log("qmdict_ocr_audio_priority_runtime_failed", error=str(exc))
            return []
        priority: list[str] = []
        seen: set[str] = set()
        total_pages = len(texts)
        # Tokenize the complete OCR snapshot once, then reuse the repository's
        # morphology/normalization validator for each unique token.
        token_seen: set[str] = set()
        tokens: list[str] = []
        for text in texts:
            for token in re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", str(text or "")):
                normalized = pdf_vocab_word_key(token)
                if normalized and normalized not in token_seen:
                    token_seen.add(normalized)
                    tokens.append(normalized)
        if callable(progress):
            progress(0, len(tokens), 0)
        line_to_word: dict[str, str] = {}
        for raw_word, raw_line in qmdict.items():
            canonical = clean(raw_word)
            if canonical:
                line_to_word.setdefault(str(raw_line), canonical)
        for token_index, token in enumerate(tokens, 1):
            if callable(cancelled) and cancelled():
                return priority
            valid_lines: list[object] = []
            try:
                viewer_vocab_runtime.is_valid_word(token, qmdict, valid_lines, number="1")
            except Exception as exc:
                stt_debug_log("qmdict_ocr_audio_priority_token_failed", token=token, error=str(exc))
                continue
            for line in valid_lines:
                canonical = line_to_word.get(str(line))
                if canonical and canonical not in seen:
                    seen.add(canonical)
                    priority.append(canonical)
            if callable(progress) and (token_index == len(tokens) or token_index % 250 == 0):
                progress(token_index, len(tokens), len(priority))
        with QMDICT_OCR_AUDIO_PRIORITY_LOCK:
            QMDICT_OCR_AUDIO_PRIORITY_CACHE.update(
                {"signature": signature, "words": list(priority), "pages": total_pages, "built_at": utc_timestamp()}
            )
        atomic_write_json(
            QMDICT_OCR_AUDIO_PRIORITY_FILE,
            {"version": 1, "source": "postgresql_ocr_cache", "words": priority, "pages": total_pages, "built_at": utc_timestamp()},
            indent=2,
        )
        return priority
    except Exception as exc:
        stt_debug_log("qmdict_ocr_audio_priority_failed", error=str(exc))
        return []


def qmdict_word_audio_refresh_entries(mode: str = "all", priority_words: object = None) -> list[tuple[str, str, str]]:
    clean_mode = clean(mode).strip().lower()
    entries: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    if clean_mode == "resume":
        try:
            payload = json.loads(QMDICT_WORD_AUDIO_REFRESH_REPORT_FILE.read_text(encoding="utf-8-sig", errors="replace"))
            raw_entries = payload.get("entries", []) if isinstance(payload, dict) else []
            if not raw_entries:
                requested_items = payload.get("requested_items") if isinstance(payload, dict) else None
                session_mode = clean(payload.get("session_mode") or payload.get("mode")).lower() if isinstance(payload, dict) else ""
                if isinstance(requested_items, list):
                    raw_entries = qmdict_selected_word_audio_refresh_entries(requested_items)
                elif session_mode in {"all", "force", "missing"}:
                    raw_entries = qmdict_word_audio_refresh_entries(session_mode, priority_words=priority_words)
            completed = {
                (clean(row.get("word")).lower(), clean(row.get("voice")).lower())
                for row in (payload.get("items", []) if isinstance(payload, dict) else [])
                if isinstance(row, dict) and clean(row.get("status")).lower() in {"refreshed", "already_present"}
            }
            for raw in raw_entries:
                if not isinstance(raw, (list, tuple)) or len(raw) < 3:
                    continue
                key, word, voice = clean(raw[0]).upper(), clean(raw[1]), normalize_space_v_refresh_voice(raw[2])
                if word and (word.lower(), voice.lower()) not in completed and (word.lower(), voice.lower()) not in seen:
                    seen.add((word.lower(), voice.lower()))
                    entries.append((key or word.upper(), word, voice))
        except Exception:
            return []
        return entries
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
    qmdict_lookup = {clean(raw_word).lower(): clean(raw_word) for raw_word in qmdict.keys() if clean(raw_word)}
    ordered_words: list[str] = []
    seen_words: set[str] = set()
    for raw_word in priority_words if isinstance(priority_words, (list, tuple, set)) else []:
        key = clean(raw_word).lower()
        word = qmdict_lookup.get(key, "")
        if word and key not in seen_words:
            seen_words.add(key)
            ordered_words.append(word)
    for raw_key in qmdict.keys():
        word = clean(raw_key)
        key = word.lower()
        if word and key not in seen_words:
            seen_words.add(key)
            ordered_words.append(word)
    for word in ordered_words:
        for voice in ("sot:en-GB", "sot:en-US"):
            pair = (word.lower(), voice.lower())
            if pair in seen:
                continue
            seen.add(pair)
            entries.append((word.upper(), word, voice))
    return entries


def qmdict_selected_word_audio_refresh_entries(items: object = None) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in items if isinstance(items, list) else []:
        if isinstance(row, dict):
            word = clean(row.get("word") or row.get("key"))
            voices = row.get("voices") if isinstance(row.get("voices"), list) else [row.get("voice")]
        else:
            word = clean(row)
            voices = ["sot:en-GB", "sot:en-US"]
        for raw_voice in voices:
            if not clean(raw_voice):
                raw_voice = "sot:en-GB"
            try:
                voice = normalize_space_v_refresh_voice(raw_voice)
            except Exception:
                continue
            pair = (word.lower(), voice.lower())
            if word and pair not in seen:
                seen.add(pair)
                entries.append((word.upper(), word, voice))
    return entries


def synthesize_qmdict_word_audio_item(key: object = "", word: object = "", voice_key: object = "", job_id: object = "", force: bool = True) -> dict:
    """Synthesize one bulk item without doing file, index, or report I/O."""
    target_key = clean(key).upper()
    target_word = normalize_qmdict_tts_word(word)
    target_voice = normalize_space_v_refresh_voice(voice_key)
    row = {"key": target_key or target_word.upper(), "word": target_word, "voice": target_voice, "status": ""}
    if not target_word:
        row.update({"status": "failed", "error": "Missing QmDict word."})
        return {"row": row, "audio_bytes": b"", "audio_source": "", "attempts": 0}
    if not force:
        existing_path = fast_qmlearn_audio_path(target_word, target_voice, allow_scan=False, use_index=True)
        if existing_path is not None and Path(existing_path).is_file() and Path(existing_path).stat().st_size > 0:
            row.update({"status": "already_present", "path": qmlearn_data_relative_path(existing_path), "attempts": 0})
            return {"row": row, "audio_bytes": b"", "audio_source": "", "attempts": 0}
    last_error = ""
    for attempt in range(1, 4):
        if qmdict_word_audio_refresh_cancel_requested(job_id):
            row.update({"status": "cancelled", "error": "Refresh cancelled."})
            return {"row": row, "audio_bytes": b"", "audio_source": "", "attempts": attempt}
        try:
            invalidate_qmlearn_audio_path_cache(target_word, target_voice)
            audio_bytes, audio_source = synthesize_bulk_audio_worker_first(
                target_word,
                target_voice,
                lambda message: stt_debug_log(
                    "qmdict_word_audio_refresh",
                    key=target_key,
                    word=target_word,
                    voice=target_voice,
                    attempt=attempt,
                    message=message,
                ),
            )
            return {"row": row, "audio_bytes": audio_bytes, "audio_source": audio_source, "attempts": attempt}
        except Exception as exc:
            last_error = str(exc)
            if attempt < 3 and not qmdict_word_audio_refresh_cancel_requested(job_id):
                time.sleep(0.7 * attempt)
    row.update({"status": "failed", "error": last_error or "Unknown audio synthesis error.", "attempts": 3})
    return {"row": row, "audio_bytes": b"", "audio_source": "", "attempts": 3}


# Added 2026-07-31: bounded writer stage keeps distributed TTS slots full while
# MP3 replacement, revision invalidation, and registry updates complete behind it.
def persist_qmdict_word_audio_item(result: dict, job_id: object = "") -> dict:
    row = dict(result.get("row") if isinstance(result, dict) and isinstance(result.get("row"), dict) else {})
    target_word = clean(row.get("word"))
    target_voice = clean(row.get("voice"))
    target_key = clean(row.get("key")).upper()
    if clean(row.get("status")) in {"already_present", "cancelled", "failed"}:
        return row
    audio_bytes = result.get("audio_bytes") if isinstance(result, dict) else b""
    audio_source = clean(result.get("audio_source")) if isinstance(result, dict) else ""
    synthesis_attempts = max(1, int(result.get("attempts", 1) or 1)) if isinstance(result, dict) else 1
    if not target_word or not target_voice or not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
        row.update({"status": "failed", "error": "Audio synthesis returned no bytes.", "attempts": synthesis_attempts})
        return row
    last_error = ""
    for persist_attempt in range(1, 4):
        if qmdict_word_audio_refresh_cancel_requested(job_id):
            row.update({"status": "cancelled", "error": "Refresh cancelled."})
            return row
        try:
            saved_path = force_save_space_v_sound_audio(
                target_word,
                target_voice,
                audio_bytes,
                lambda message: stt_debug_log("qmdict_word_audio_refresh", key=target_key, word=target_word, voice=target_voice, attempt=synthesis_attempts, message=message),
            )
            refresh_qmlearn_audio_dir_index_entry(target_word, target_voice)
            invalidate_qmlearn_audio_path_cache(target_word, target_voice)
            invalidate_space_v_audio_payload_cache_for_word(target_word)
            audio_path = saved_path if saved_path and Path(saved_path).is_file() else fast_qmlearn_audio_path(target_word, target_voice, allow_scan=False, use_index=False)
            if audio_path is not None and Path(audio_path).is_file():
                row.update(
                    {
                        "status": "refreshed",
                        "path": qmlearn_data_relative_path(audio_path),
                        "attempts": synthesis_attempts,
                        "persist_attempts": persist_attempt,
                        "source": audio_source,
                    }
                )
                return row
            raise RuntimeError("Audio file was not saved after synthesis.")
        except Exception as exc:
            last_error = str(exc)
            if persist_attempt < 3 and not qmdict_word_audio_refresh_cancel_requested(job_id):
                time.sleep(0.25 * persist_attempt)
    row.update({"status": "failed", "error": last_error or "Unknown audio persistence error.", "attempts": synthesis_attempts, "persist_attempts": 3})
    return row


def refresh_qmdict_word_audio_item(key: object = "", word: object = "", voice_key: object = "", job_id: object = "", force: bool = True) -> dict:
    return persist_qmdict_word_audio_item(
        synthesize_qmdict_word_audio_item(key, word, voice_key, job_id, force),
        job_id,
    )


def run_qmdict_word_audio_refresh_job(job_id: str, mode: str = "all", requested_items: object = None) -> None:
    done = refreshed = failed = scanned = priority_done = 0
    resume_done_offset = resume_refreshed_offset = resume_failed_offset = 0
    resume_session_total = 0
    resume_requested_items = None
    report_rows: list[dict] = []
    try:
        verify_qmdict_word_audio_runtime()
        ensure_qmdict_runtime_fresh(force=True)
        session_mode = mode
        resume_has_selected_items = False
        if mode == "resume":
            try:
                previous_report = json.loads(QMDICT_WORD_AUDIO_REFRESH_REPORT_FILE.read_text(encoding="utf-8-sig", errors="replace"))
                session_mode = clean(previous_report.get("session_mode") or previous_report.get("mode")).lower() or "missing"
                resume_requested_items = previous_report.get("requested_items") if isinstance(previous_report.get("requested_items"), list) else None
                resume_has_selected_items = isinstance(resume_requested_items, list)
                resume_session_total = max(0, int(previous_report.get("session_base_total", previous_report.get("session_total", previous_report.get("total", 0))) or 0))
                resume_done_offset = max(0, int(previous_report.get("session_done", previous_report.get("done", 0)) or 0))
                resume_refreshed_offset = max(0, int(previous_report.get("session_refreshed", previous_report.get("refreshed", 0)) or 0))
                resume_failed_offset = max(0, int(previous_report.get("session_failed", previous_report.get("failed", 0)) or 0))
            except Exception:
                session_mode = "missing"
        priority_words: list[str] = []
        if (
            not isinstance(requested_items, list)
            and not resume_has_selected_items
            and session_mode in {"all", "force", "missing"}
            and QMDICT_OCR_AUDIO_PRIORITY_FILE.is_file()
        ):
            def update_priority_progress(page_done: int, page_total: int, word_total: int) -> None:
                with QMDICT_WORD_AUDIO_REFRESH_LOCK:
                    if clean(QMDICT_WORD_AUDIO_REFRESH_JOB.get("job_id")) != clean(job_id):
                        return
                    QMDICT_WORD_AUDIO_REFRESH_JOB.update(
                        {
                            "phase": "prioritizing",
                            "message": "Matching unique PostgreSQL OCR tokens with QmDict.",
                            "scan_total": max(0, int(page_total or 0)),
                            "scan_done": max(0, int(page_done or 0)),
                            "priority_total": max(0, int(word_total or 0)) * 2,
                            "priority_done": 0,
                            "updated_at": utc_timestamp(),
                        }
                    )
                    priority_snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
                write_qmdict_word_audio_refresh_progress({"version": 1, **priority_snapshot})

            priority_words = qmdict_ocr_audio_priority_words(
                progress=update_priority_progress,
                cancelled=lambda: qmdict_word_audio_refresh_cancel_requested(job_id),
            )
        entries = [] if qmdict_word_audio_refresh_cancel_requested(job_id) else (
            qmdict_selected_word_audio_refresh_entries(requested_items)
            if isinstance(requested_items, list)
            else qmdict_word_audio_refresh_entries(mode, priority_words=priority_words)
        )
        if mode == "resume":
            if resume_has_selected_items:
                resume_session_total = len(qmdict_selected_word_audio_refresh_entries(resume_requested_items))
            elif session_mode in {"all", "force"}:
                resume_session_total = len(qmdict_word_audio_refresh_entries("all"))
            resume_session_total = max(len(entries), resume_session_total)
            # Remaining entries already include every failed/cancelled item that
            # must be retried; derive the stable checkpoint from the session scope.
            resume_done_offset = max(0, resume_session_total - len(entries))
            resume_refreshed_offset = min(resume_refreshed_offset, resume_done_offset)
            resume_failed_offset = 0
        force_refresh = mode in {"all", "force", "selected-force"}
        if mode == "resume":
            force_refresh = session_mode in {"all", "force", "selected-force"}
        if mode in {"missing", "selected-missing"}:
            missing_entries = []
            scan_candidates = len(entries)
            for scan_index, item in enumerate(entries, 1):
                if qmdict_word_audio_refresh_cancel_requested(job_id):
                    missing_entries = []
                    break
                audio_path = fast_qmlearn_audio_path(item[1], item[2], allow_scan=False, use_index=True)
                try:
                    valid = audio_path is not None and Path(audio_path).is_file() and Path(audio_path).stat().st_size > 0
                except OSError:
                    valid = False
                if not valid:
                    missing_entries.append(item)
                if scan_index == scan_candidates or scan_index % 250 == 0:
                    with QMDICT_WORD_AUDIO_REFRESH_LOCK:
                        QMDICT_WORD_AUDIO_REFRESH_JOB.update(
                            {
                                "phase": "scanning",
                                "message": "Checking existing UK/US audio files in OCR-first order.",
                                "scan_total": scan_candidates,
                                "scan_done": scan_index,
                                "total": len(missing_entries),
                                "updated_at": utc_timestamp(),
                            }
                        )
                        scan_snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
                    write_qmdict_word_audio_refresh_progress({"version": 1, **scan_snapshot})
            entries = missing_entries
        priority_word_keys = {clean(word).lower() for word in priority_words if clean(word)}
        priority_entry_keys = {
            (clean(word).lower(), clean(voice).lower())
            for _key, word, voice in entries
            if clean(word).lower() in priority_word_keys
        }
        priority_total = len(priority_entry_keys)
        total = len(entries)
        session_total = resume_session_total if mode == "resume" and resume_session_total else total
        report_requested_items = requested_items if isinstance(requested_items, list) else resume_requested_items
        worker_count = qmdict_bulk_audio_concurrency(total)
        with QMDICT_WORD_AUDIO_REFRESH_LOCK:
            QMDICT_WORD_AUDIO_REFRESH_JOB.update(
                {
                    "phase": "downloading" if total else "complete",
                    "message": f"Refreshing QmDict UK/US word audio with {worker_count} SOT slots." if total else "No QmDict word audio needs retry.",
                    "scan_total": total,
                    "scan_done": total,
                    "workers": worker_count,
                    "total": session_total,
                    "done": resume_done_offset,
                    "refreshed": resume_refreshed_offset,
                    "failed": resume_failed_offset,
                    "session_total": session_total,
                    "session_base_total": session_total,
                    "session_done": resume_done_offset,
                    "session_refreshed": resume_refreshed_offset,
                    "session_failed": resume_failed_offset,
                    "priority_total": priority_total,
                    "priority_done": 0,
                    "last_key": "",
                    "last_word": "",
                    "last_voice": "",
                    "updated_at": utc_timestamp(),
                    "error": "",
                    "cancel_requested": bool(QMDICT_WORD_AUDIO_REFRESH_JOB.get("cancel_requested")),
                }
            )
            snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
        atomic_write_json(QMDICT_WORD_AUDIO_REFRESH_REPORT_FILE, {"version": 1, **snapshot, "session_mode": session_mode, "entries": entries, "requested_items": report_requested_items, "items": []}, indent=2)
        write_qmdict_word_audio_refresh_progress({"version": 1, **snapshot})
        if entries:
            synthesis_executor = concurrent.futures.ThreadPoolExecutor(max_workers=min(128, total), thread_name_prefix="qmdict-word-synthesis")
            writer_workers = max(1, min(int(QMDICT_WORD_AUDIO_WRITER_WORKERS or 8), total))
            writer_executor = concurrent.futures.ThreadPoolExecutor(max_workers=writer_workers, thread_name_prefix="qmdict-word-writer")
            result_buffer_limit = max(writer_workers, int(QMDICT_WORD_AUDIO_RESULT_BUFFER or 128))
            synthesis_futures = {}
            writer_futures = {}
            next_index = 0

            def fill_word_audio_capacity() -> None:
                nonlocal next_index, worker_count
                desired = qmdict_bulk_audio_concurrency(len(entries) - done)
                worker_count = desired
                while not qmdict_word_audio_refresh_cancel_requested(job_id) and len(synthesis_futures) < desired and next_index < len(entries):
                    key, word, voice = entries[next_index]
                    next_index += 1
                    synthesis_futures[synthesis_executor.submit(synthesize_qmdict_word_audio_item, key, word, voice, job_id, force_refresh)] = (key, word, voice)
                with QMDICT_WORD_AUDIO_REFRESH_LOCK:
                    QMDICT_WORD_AUDIO_REFRESH_JOB.update(
                        {
                            "workers": desired,
                            "writers": writer_workers,
                            "writer_pending": len(writer_futures),
                            "result_buffer_limit": result_buffer_limit,
                        }
                    )

            def record_word_audio_row(row: dict, key: str, word: str, voice: str) -> None:
                nonlocal done, refreshed, failed, scanned, priority_done, snapshot
                status = clean(row.get("status", "")).lower()
                if status != "cancelled":
                    done += 1
                    scanned += 1
                if status == "refreshed":
                    refreshed += 1
                elif status not in {"cancelled", "already_present"}:
                    failed += 1
                report_rows.append(row)
                if (clean(row.get("word") or word).lower(), clean(row.get("voice") or voice).lower()) in priority_entry_keys:
                    priority_done += 1
                with QMDICT_WORD_AUDIO_REFRESH_LOCK:
                    QMDICT_WORD_AUDIO_REFRESH_JOB.update(
                        {
                            "done": resume_done_offset + done,
                            "scan_done": scanned,
                            "refreshed": resume_refreshed_offset + refreshed,
                            "failed": resume_failed_offset + failed,
                            "session_total": session_total,
                            "session_done": resume_done_offset + done,
                            "session_refreshed": resume_refreshed_offset + refreshed,
                            "session_failed": resume_failed_offset + failed,
                            "priority_done": priority_done,
                            "writer_pending": len(writer_futures),
                            "last_key": clean(row.get("key") or key),
                            "last_word": clean(row.get("word") or word)[:180],
                            "last_voice": clean(row.get("voice") or voice),
                            "updated_at": utc_timestamp(),
                        }
                    )
                    snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
                if done == total or (status != "cancelled" and done % 50 == 0) or status not in {"refreshed", "cancelled"}:
                    atomic_write_json(QMDICT_WORD_AUDIO_REFRESH_REPORT_FILE, {"version": 1, **snapshot, "session_mode": session_mode, "entries": entries, "requested_items": report_requested_items, "items": report_rows}, indent=2)
                    write_qmdict_word_audio_refresh_progress({"version": 1, **snapshot})

            fill_word_audio_capacity()
            try:
                while synthesis_futures or writer_futures:
                    if qmdict_word_audio_refresh_cancel_requested(job_id):
                        for future in synthesis_futures:
                            future.cancel()
                    ready_writers = {future for future in writer_futures if future.done()}
                    if not ready_writers and writer_futures and (len(writer_futures) >= result_buffer_limit or not synthesis_futures):
                        ready_writers, _pending = concurrent.futures.wait(writer_futures, timeout=1.0, return_when=concurrent.futures.FIRST_COMPLETED)
                    for future in ready_writers:
                        key, word, voice = writer_futures.pop(future)
                        try:
                            row = future.result()
                        except concurrent.futures.CancelledError:
                            row = {"key": key, "word": word, "voice": voice, "status": "cancelled", "error": "Refresh cancelled."}
                        except Exception as exc:
                            row = {"key": key, "word": word, "voice": voice, "status": "failed", "error": str(exc)}
                        record_word_audio_row(row, key, word, voice)
                    if synthesis_futures and len(writer_futures) < result_buffer_limit:
                        ready_synthesis, _pending = concurrent.futures.wait(synthesis_futures, timeout=0.05, return_when=concurrent.futures.FIRST_COMPLETED)
                        available_writer_slots = max(0, result_buffer_limit - len(writer_futures))
                        for future in list(ready_synthesis)[:available_writer_slots]:
                            key, word, voice = synthesis_futures.pop(future)
                            try:
                                result = future.result()
                            except concurrent.futures.CancelledError:
                                result = {"row": {"key": key, "word": word, "voice": voice, "status": "cancelled", "error": "Refresh cancelled."}}
                            except Exception as exc:
                                result = {"row": {"key": key, "word": word, "voice": voice, "status": "failed", "error": str(exc)}}
                            writer_futures[writer_executor.submit(persist_qmdict_word_audio_item, result, job_id)] = (key, word, voice)
                            # Refill immediately after the worker returns bytes; file,
                            # index and report work continues in the bounded writer stage.
                            fill_word_audio_capacity()
                    elif not ready_writers:
                        time.sleep(0.01)
            finally:
                synthesis_executor.shutdown(wait=True, cancel_futures=True)
                writer_executor.shutdown(wait=True, cancel_futures=True)
        cancelled = qmdict_word_audio_refresh_cancel_requested(job_id)
        completed_at = utc_timestamp()
        with QMDICT_WORD_AUDIO_REFRESH_LOCK:
            QMDICT_WORD_AUDIO_REFRESH_JOB.update(
                {
                    "running": False,
                    "phase": "cancelled" if cancelled else "complete",
                    "message": "QmDict UK/US word audio refresh cancelled." if cancelled else "QmDict UK/US word audio refresh complete.",
                    "completed_at": completed_at,
                    "updated_at": completed_at,
                }
            )
            final_snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
        atomic_write_json(
            QMDICT_WORD_AUDIO_REFRESH_REPORT_FILE,
            {"version": 1, **final_snapshot, "session_mode": session_mode, "entries": entries, "requested_items": report_requested_items, "items": report_rows},
            indent=2,
        )
        write_qmdict_word_audio_refresh_progress({"version": 1, **final_snapshot})
        stt_debug_log("qmdict_word_audio_refresh_done", job_id=job_id, mode=mode, total=total, refreshed=refreshed, failed=failed, cancelled=cancelled)
    except Exception as exc:
        with QMDICT_WORD_AUDIO_REFRESH_LOCK:
            QMDICT_WORD_AUDIO_REFRESH_JOB.update(
                {
                    "running": False,
                    "phase": "failed",
                    "message": "QmDict UK/US word audio refresh failed.",
                    "updated_at": utc_timestamp(),
                    "error": str(exc),
                    "cancel_requested": False,
                }
            )
            snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
        write_qmdict_word_audio_refresh_progress({"version": 1, **snapshot})
        stt_debug_log("qmdict_word_audio_refresh_failed", job_id=job_id, mode=mode, error=str(exc))


def start_qmdict_word_audio_refresh(mode: str = "all", items: object = None) -> dict:
    clean_mode = clean(mode).strip().lower() or "all"
    selected_items = items if isinstance(items, list) else None
    if selected_items is not None:
        selected_items = selected_items[:1000]
        if clean_mode in {"force", "all"}:
            clean_mode = "selected-force"
        elif clean_mode == "missing":
            clean_mode = "selected-missing"
        else:
            clean_mode = "selected"
    if clean_mode not in {"all", "force", "missing", "failed", "retry", "retry-failed", "resume", "selected", "selected-force", "selected-missing"}:
        clean_mode = "all"
    if clean_mode in {"retry", "retry-failed"}:
        clean_mode = "failed"
    resume_seed = {}
    if clean_mode == "resume":
        try:
            saved = json.loads(QMDICT_WORD_AUDIO_REFRESH_REPORT_FILE.read_text(encoding="utf-8-sig", errors="replace"))
            resume_seed = {
                "total": max(0, int(saved.get("session_total", saved.get("total", 0)) or 0)),
                "done": max(0, int(saved.get("session_done", saved.get("done", 0)) or 0)),
                "refreshed": max(0, int(saved.get("session_refreshed", saved.get("refreshed", 0)) or 0)),
                "failed": max(0, int(saved.get("session_failed", saved.get("failed", 0)) or 0)),
            }
        except Exception:
            resume_seed = {}
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
                "total": int(resume_seed.get("total", 0) or 0),
                "done": int(resume_seed.get("done", 0) or 0),
                "refreshed": int(resume_seed.get("refreshed", 0) or 0),
                "failed": int(resume_seed.get("failed", 0) or 0),
                "priority_total": 0,
                "priority_done": 0,
                "last_key": "",
                "last_word": "",
                "last_voice": "",
                "error": "",
                "cancel_requested": False,
            }
        )
        snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
    if clean_mode not in {"resume", "failed"}:
        seed_entries = qmdict_selected_word_audio_refresh_entries(selected_items) if selected_items is not None else []
        atomic_write_json(
            QMDICT_WORD_AUDIO_REFRESH_REPORT_FILE,
            {
                "version": 1,
                **snapshot,
                "session_mode": clean_mode,
                "entries": seed_entries,
                "requested_items": selected_items,
                "items": [],
            },
            indent=2,
        )
        write_qmdict_word_audio_refresh_progress({"version": 1, **snapshot})
    threading.Thread(
        target=run_qmdict_word_audio_refresh_job,
        args=(job_id, clean_mode, selected_items),
        name=f"qmdict-word-audio-refresh-{job_id[:8]}",
        daemon=True,
    ).start()
    if clean_mode in {"resume", "failed"}:
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
    # Exact resolver/index lookup avoids rebuilding the legacy root stem scan.
    if not text or qmdict_meaning_audio_local_path(text) is None:
        return {}
    asset = qmlearn_meaning_audio_asset(text)
    revision = clean(asset.get("revision")) or "0"
    return {
        "m": "audio/mpeg",
        "u": qm_sound_protocol_url(meaning=text, file_revision=revision),
        "aid": clean(asset.get("asset_id")),
        "src": "QMLearn/Data/meaning-lazy",
    }


# Added 2026-07-31: every shared QmSound URL carries one durable epoch and exact file revision.
def qm_sound_protocol_url(
    *,
    word: object = "",
    voice: object = "",
    meaning: object = "",
    rel_path: object = "",
    file_revision: object = "",
) -> str:
    parts = []
    if clean(meaning):
        parts.append(f"meaning={quote(clean(meaning), safe='')}")
    elif clean(word):
        parts.append(f"word={quote(clean(word), safe='')}")
        parts.append(f"voice={quote(clean(voice), safe='')}")
    elif clean_path_value(rel_path):
        parts.append(f"path={quote(clean_path_value(rel_path), safe='')}")
    revision = clean(file_revision) or "0"
    parts.append(f"audio_epoch={global_audio_cache_epoch()}")
    parts.append(f"file_rev={quote(revision, safe='')}")
    return "/server-data/qm-sound?" + "&".join(parts)


# Added 2026-07-31: direct frontend callers resolve one exact immutable URL before fetching audio.
def qm_sound_protocol_descriptor(
    *,
    word: object = "",
    voice: object = "",
    meaning: object = "",
    rel_path: object = "",
) -> dict:
    target = None
    if clean(meaning):
        target = qmlearn_meaning_audio_asset(meaning).get("path")
    elif clean(word):
        target = qmlearn_word_audio_asset(word, voice).get("path")
    elif clean_path_value(rel_path):
        target = safe_qmlearn_data_sound_path(clean_path_value(rel_path))
    if not target or not Path(target).is_file():
        raise RuntimeError("Audio QMLearn khong ton tai.")
    revision = qmlearn_audio_file_revision(target)
    if not revision:
        raise RuntimeError("Khong doc duoc revision audio QMLearn.")
    return {
        "path": target,
        "audio_epoch": global_audio_cache_epoch(),
        "file_revision": revision,
        "url": qm_sound_protocol_url(
            word=word,
            voice=voice,
            meaning=meaning,
            rel_path=rel_path,
            file_revision=revision,
        ),
    }


def qmlearn_sound_url_for_audio_path(audio_path: object = None, fallback_query: str = "") -> str:
    rel_path = qmlearn_data_relative_path(audio_path)
    if rel_path:
        cache_key = rel_path.lower()
        version = qmlearn_audio_file_revision(audio_path)
        protocol_signature = f"{global_audio_cache_epoch()}|{version}"
        with QMLEARN_AUDIO_URL_CACHE_LOCK:
            cached = QMLEARN_AUDIO_URL_CACHE.get(cache_key)
            if cached and cached[0] == protocol_signature and cached[1]:
                return cached[1]
        url = qm_sound_protocol_url(rel_path=rel_path, file_revision=version)
        if version:
            with QMLEARN_AUDIO_URL_CACHE_LOCK:
                QMLEARN_AUDIO_URL_CACHE[cache_key] = (protocol_signature, url)
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
                normalized_voice = clean(voice_key)
                accent_key = "u" if normalized_voice.lower().endswith("en-us") else "g"
                asset = qmlearn_word_audio_asset(target_word, normalized_voice)
                revision = clean(asset.get("revision")) or "0"
                sound_url = qm_sound_protocol_url(word=target_word, voice=normalized_voice, file_revision=revision)
                clip = {
                    "m": "audio/mpeg",
                    "u": sound_url,
                    "aid": f"v3:w:{vocab_key(target_word)}:{accent_key}:{global_audio_cache_epoch()}:{revision}",
                    "src": "QMLearn/Data/epoch-revision",
                }
                audio[voice_key] = clip
                audio[short_key] = clip
        meaning_text = clean(meaning)
        if meaning_text:
            digest = hashlib.sha256(meaning_text.lower().encode("utf-8")).hexdigest()[:32]
            meaning_asset = qmlearn_meaning_audio_asset(meaning_text)
            meaning_revision = clean(meaning_asset.get("revision")) or "0"
            meaning_clip = {
                "m": "audio/mpeg",
                "u": qm_sound_protocol_url(meaning=meaning_text, file_revision=meaning_revision),
                "aid": f"v3:m:{digest}:{global_audio_cache_epoch()}:{meaning_revision}",
                "src": "QMLearn/Data/meaning-epoch-revision",
            }
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


SPACE_V_LOCAL_PICTURE_INDEX_LOCK = threading.RLock()
SPACE_V_LOCAL_PICTURE_INDEX_STATE = {
    "folder": "",
    "folder_signature": None,
    "entries": {},
    "indexed_files": 0,
    "duplicate_words": 0,
    "ignored_files": 0,
    "exists": False,
    "built_at": "",
    "next_check_at": 0.0,
}
SPACE_V_LOCAL_PICTURE_INDEX_CHECK_SECONDS = 5.0
SPACE_V_LOCAL_PICTURE_SUFFIX_PRIORITY = {
    ".png": 0,
    ".webp": 1,
    ".jpg": 2,
    ".jpeg": 3,
    ".jfif": 4,
    ".gif": 5,
    ".bmp": 6,
}


# Added 2026-07-30: invalidate one shared local picture index after the PostgreSQL-backed folder setting changes.
def invalidate_space_v_local_picture_index() -> None:
    with SPACE_V_LOCAL_PICTURE_INDEX_LOCK:
        SPACE_V_LOCAL_PICTURE_INDEX_STATE.update({
            "folder": "",
            "folder_signature": None,
            "entries": {},
            "indexed_files": 0,
            "duplicate_words": 0,
            "ignored_files": 0,
            "exists": False,
            "built_at": "",
            "next_check_at": 0.0,
        })


def _space_v_local_picture_folder_signature(folder: Path) -> tuple[int, int]:
    try:
        stat = folder.stat()
        return int(stat.st_mtime_ns), int(getattr(stat, "st_ino", 0) or 0)
    except Exception:
        return 0, 0


def _space_v_local_picture_build(folder: Path) -> dict:
    grouped_entries: dict[str, dict[int, dict]] = {}
    indexed_files = 0
    duplicate_words = 0
    ignored_files = 0
    if folder.is_dir():
        try:
            with os.scandir(folder) as iterator:
                for item in iterator:
                    try:
                        if not item.is_file(follow_symlinks=False):
                            continue
                        path = Path(item.path)
                        suffix = path.suffix.lower()
                        priority = SPACE_V_LOCAL_PICTURE_SUFFIX_PRIORITY.get(suffix)
                        stem_match = re.fullmatch(r"(.+?)(\d+)?", path.stem.strip())
                        base_stem = clean(stem_match.group(1) if stem_match else path.stem)
                        variant = max(0, int(stem_match.group(2) or 0)) if stem_match else 0
                        key = vocab_key(base_stem)
                        if priority is None or not key:
                            ignored_files += 1
                            continue
                        stat = item.stat(follow_symlinks=False)
                        candidate = {
                            "path": str(path),
                            "name": item.name,
                            "size": int(stat.st_size),
                            "mtime_ns": int(stat.st_mtime_ns),
                            "priority": int(priority),
                            "variant": variant,
                            "word": base_stem,
                            "image_id": item.name.casefold(),
                        }
                        candidate["revision"] = f"{candidate['mtime_ns']:x}-{candidate['size']:x}"
                        variants = grouped_entries.setdefault(key, {})
                        current = variants.get(variant)
                        if current is not None:
                            duplicate_words += 1
                            current_order = (int(current.get("priority", 99)), clean(current.get("name", "")).casefold())
                            candidate_order = (priority, item.name.casefold())
                            if candidate_order >= current_order:
                                continue
                        variants[variant] = candidate
                        indexed_files += 1
                    except OSError:
                        ignored_files += 1
        except OSError as exc:
            stt_debug_log("space_v_local_picture_scan_failed", folder=str(folder), error=str(exc))
    entries = {
        key: [dict(record) for _variant, record in sorted(variants.items(), key=lambda item: (int(item[0]), clean(item[1].get("name", "")).casefold()))]
        for key, variants in grouped_entries.items()
        if variants
    }
    return {
        "folder": str(folder),
        "folder_signature": _space_v_local_picture_folder_signature(folder),
        "entries": entries,
        "indexed_files": indexed_files,
        "duplicate_words": duplicate_words,
        "ignored_files": ignored_files,
        "exists": folder.is_dir(),
        "built_at": utc_timestamp(),
        "next_check_at": time.monotonic() + SPACE_V_LOCAL_PICTURE_INDEX_CHECK_SECONDS,
    }


# Added 2026-07-30: scan the configured flat folder once, then reuse immutable RAM metadata for O(1) word lookup.
def ensure_space_v_local_picture_index(force: bool = False) -> dict:
    now = time.monotonic()
    with SPACE_V_LOCAL_PICTURE_INDEX_LOCK:
        state = SPACE_V_LOCAL_PICTURE_INDEX_STATE
        folder_text = clean(state.get("folder", ""))
        if not folder_text:
            settings = load_server_settings()
            folder_text = normalize_space_v_picture_folder(settings.get("space_v_picture_folder", ""))
        folder = Path(folder_text)
        if not force and clean(state.get("folder", "")) == folder_text:
            if float(state.get("next_check_at", 0) or 0) > now:
                return state
            signature = _space_v_local_picture_folder_signature(folder)
            if state.get("folder_signature") == signature:
                state["next_check_at"] = now + SPACE_V_LOCAL_PICTURE_INDEX_CHECK_SECONDS
                return state
        next_state = _space_v_local_picture_build(folder)
        state.clear()
        state.update(next_state)
        return state


def space_v_local_picture_assets(word: object = "") -> list[dict]:
    # Added 2026-08-04: one O(1) word lookup returns its pre-indexed word/word1/word2 gallery without rescanning the folder.
    target_word = clean(word)
    key = vocab_key(target_word)
    if not key:
        return []
    ensure_space_v_local_picture_index()
    with SPACE_V_LOCAL_PICTURE_INDEX_LOCK:
        entries = SPACE_V_LOCAL_PICTURE_INDEX_STATE.get("entries", {})
        records = entries.get(key) if isinstance(entries, dict) else None
        return [dict(record) for record in records if isinstance(record, dict)] if isinstance(records, list) else []


def space_v_local_picture_asset(word: object = "", image_id: object = "") -> dict:
    records = space_v_local_picture_assets(word)
    wanted = clean(image_id).casefold()
    if wanted:
        for record in records:
            if clean(record.get("image_id", "")).casefold() == wanted:
                return record
        return {}
    return records[0] if records else {}


def qmdict_space_v_image_lookup(word: object = "") -> dict:
    target_word = clean(word)
    records = space_v_local_picture_assets(target_word)
    images = [{
        "id": clean(record.get("image_id", "")),
        "u": f"/vocab/image-file?word={quote(target_word, safe='')}&image_id={quote(clean(record.get('image_id', '')), safe='')}&rev={quote(clean(record.get('revision', '')), safe='')}",
        "s": "Local picture folder",
        "c": target_word,
        "n": max(0, int(record.get("variant", 0) or 0)),
        "revision": clean(record.get("revision", "")),
    } for record in records]
    return {"image": images[0] if images else {}, "images": images, "pending": False, "retry_after_ms": 0}


def qmdict_space_v_dynamic_image(word: object = "") -> dict:
    return dict(qmdict_space_v_image_lookup(word).get("image") or {})


def qmdict_space_v_cached_image(word: object = "") -> dict:
    return qmdict_space_v_dynamic_image(word)


def space_v_local_picture_settings_payload(force: bool = False) -> dict:
    ensure_space_v_local_picture_index(force=force)
    with SPACE_V_LOCAL_PICTURE_INDEX_LOCK:
        state = SPACE_V_LOCAL_PICTURE_INDEX_STATE
        return {
            "folder": clean(state.get("folder", "")),
            "exists": bool(state.get("exists")),
            "indexed_files": max(0, int(state.get("indexed_files", 0) or 0)),
            "matched_words": len(state.get("entries", {})) if isinstance(state.get("entries"), dict) else 0,
            "gallery_images": sum(len(records) for records in state.get("entries", {}).values() if isinstance(records, list)) if isinstance(state.get("entries"), dict) else 0,
            "duplicate_words": max(0, int(state.get("duplicate_words", 0) or 0)),
            "ignored_files": max(0, int(state.get("ignored_files", 0) or 0)),
            "built_at": clean(state.get("built_at", "")),
        }


def warm_space_v_local_picture_index_async(delay_seconds: float = 0.0) -> None:
    def worker() -> None:
        if delay_seconds > 0:
            time.sleep(max(0.0, float(delay_seconds)))
        try:
            space_v_local_picture_settings_payload(force=True)
        except Exception as exc:
            stt_debug_log("space_v_local_picture_warm_failed", error=str(exc))

    threading.Thread(target=worker, name="space-v-local-picture-index", daemon=True).start()


def prefetch_space_v_images_for_entries(entries: object, limit: int = 120) -> None:
    ensure_space_v_local_picture_index()


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
    downloaded = cached = failed = done = scanned = 0
    resume_done_offset = resume_downloaded_offset = resume_failed_offset = 0
    resume_session_total = 0
    resume_requested_keys = None
    report_rows: list[dict] = []
    try:
        verify_qmdict_word_audio_runtime()
        ensure_qmdict_runtime_fresh(force=True)
        clean_mode = clean(mode).lower() or "missing"
        session_mode = clean_mode
        force_refresh = clean_mode == "force"
        resume = clean_mode == "resume"
        entries = qmdict_audio_refresh_entries(keys)
        if resume:
            try:
                saved = json.loads(QMDICT_AUDIO_REFRESH_REPORT_FILE.read_text(encoding="utf-8-sig", errors="replace"))
                session_mode = clean(saved.get("session_mode") or saved.get("mode")).lower() or "missing"
                force_refresh = session_mode == "force"
                resume_requested_keys = saved.get("requested_keys") if isinstance(saved.get("requested_keys"), list) else None
                resume_session_total = max(0, int(saved.get("session_base_total", saved.get("session_total", saved.get("total", 0))) or 0))
                resume_downloaded_offset = max(0, int(saved.get("session_downloaded", saved.get("downloaded", 0)) or 0))
                resume_failed_offset = max(0, int(saved.get("session_failed", saved.get("failed", 0)) or 0))
                raw_entries = saved.get("entries", []) if isinstance(saved, dict) else []
                if not raw_entries:
                    raw_entries = qmdict_audio_refresh_entries(saved.get("requested_keys") if isinstance(saved, dict) else None)
                completed = {(clean(row.get("key")).upper(), clean(row.get("meaning")).lower()) for row in saved.get("items", []) if isinstance(row, dict) and clean(row.get("status")).lower() in {"downloaded", "cached-late", "cached-mp3"}}
                entries = [(clean(row[0]).upper(), clean(row[1])) for row in raw_entries if isinstance(row, (list, tuple)) and len(row) > 1 and clean(row[0]).upper() and clean(row[1]) and (clean(row[0]).upper(), clean(row[1]).lower()) not in completed]
            except Exception:
                session_mode = "missing"
                entries = []
        scan_total = len(entries)
        missing_entries: list[tuple[str, str]] = []
        for key, meaning in entries:
            scanned += 1
            present = False
            try:
                present = qmdict_meaning_audio_local_path(meaning) is not None
            except Exception:
                present = False
            if force_refresh or not present:
                missing_entries.append((key, meaning))
            else:
                cached += 1
            if scanned == scan_total or scanned % 100 == 0:
                with QMDICT_AUDIO_REFRESH_LOCK:
                    QMDICT_AUDIO_REFRESH_JOB.update({"phase": "scanning", "scan_total": scan_total, "scan_done": scanned, "cached": cached, "missing": len(missing_entries), "last_key": key, "last_meaning": meaning[:180], "updated_at": utc_timestamp()})
                    snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
                write_qmdict_audio_refresh_progress({"version": 1, **snapshot})
        remaining_total = len(missing_entries)
        if resume:
            if session_mode == "force" and not resume_requested_keys:
                resume_session_total = len(qmdict_audio_refresh_entries())
            resume_session_total = max(remaining_total, resume_session_total)
            resume_done_offset = max(0, resume_session_total - remaining_total)
            resume_downloaded_offset = min(resume_downloaded_offset, resume_done_offset)
            resume_failed_offset = 0
            downloaded = resume_downloaded_offset
            cached = max(cached, resume_done_offset - resume_downloaded_offset)
        session_total = resume_session_total if resume and resume_session_total else remaining_total
        session_entries = list(missing_entries)
        report_requested_keys = keys if isinstance(keys, list) else resume_requested_keys
        worker_count = qmdict_bulk_audio_concurrency(remaining_total)
        with QMDICT_AUDIO_REFRESH_LOCK:
            QMDICT_AUDIO_REFRESH_JOB.update({"phase": "downloading" if remaining_total else "complete", "message": f"Downloading Vietnamese audio with {worker_count} workers." if remaining_total else "All Vietnamese audio is already present.", "scan_total": scan_total, "scan_done": scanned, "workers": worker_count, "cleanup_total": 0, "cleanup_done": 0, "cleanup_deleted": 0, "total": session_total, "done": resume_done_offset, "cached": cached, "missing": remaining_total, "downloaded": downloaded, "failed": resume_failed_offset, "session_base_total": session_total, "session_total": session_total, "session_done": resume_done_offset, "session_downloaded": downloaded, "session_failed": resume_failed_offset, "updated_at": utc_timestamp()})
            snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
        atomic_write_json(QMDICT_AUDIO_REFRESH_REPORT_FILE, {"version": 1, **snapshot, "session_mode": session_mode, "entries": session_entries, "requested_keys": report_requested_keys, "items": report_rows}, indent=2)
        write_qmdict_audio_refresh_progress({"version": 1, **snapshot})

        def synthesize_meaning(item: tuple[str, str]) -> dict:
            key, meaning = item
            row = {"key": key, "meaning": meaning, "status": ""}
            if qmdict_audio_refresh_cancel_requested(job_id):
                row["status"] = "cancelled"
                return {"row": row, "audio_bytes": b"", "audio_source": ""}
            try:
                if not force_refresh:
                    local_path = qmdict_meaning_audio_local_path(meaning)
                    if local_path is not None:
                        ensure_qmlearn_data_sound_plain_mp3(local_path)
                        row["status"] = "cached-late"
                        return {"row": row, "audio_bytes": b"", "audio_source": ""}
                audio_bytes, audio_source = synthesize_bulk_audio_worker_first(
                    meaning,
                    "vi-VN",
                    lambda message: stt_debug_log("qmdict_audio_refresh", key=key, meaning=meaning, message=message),
                )
                return {"row": row, "audio_bytes": audio_bytes, "audio_source": audio_source}
            except Exception as exc:
                row.update({"status": "failed", "error": str(exc)})
                return {"row": row, "audio_bytes": b"", "audio_source": ""}

        def persist_meaning(result: dict) -> dict:
            row = dict(result.get("row") if isinstance(result, dict) and isinstance(result.get("row"), dict) else {})
            key = clean(row.get("key")).upper()
            meaning = clean(row.get("meaning"))
            if clean(row.get("status")) in {"cached-late", "cancelled", "failed"}:
                return row
            if qmdict_audio_refresh_cancel_requested(job_id):
                row["status"] = "cancelled"
                return row
            try:
                audio_bytes = result.get("audio_bytes") if isinstance(result, dict) else b""
                audio_source = clean(result.get("audio_source")) if isinstance(result, dict) else ""
                if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
                    raise RuntimeError("Vietnamese synthesis returned no bytes.")
                saved_path = force_save_space_v_sound_audio(meaning, "vi-VN", audio_bytes)
                refresh_qmlearn_audio_dir_index_entry(meaning, "vi-VN")
                if saved_path and Path(saved_path).is_file():
                    row["status"] = "downloaded"
                    row["path"] = qmlearn_data_relative_path(saved_path)
                    row["source"] = audio_source
                else:
                    row["status"] = "missing"
            except Exception as exc:
                row.update({"status": "failed", "error": str(exc)})
            return row

        if missing_entries:
            synthesis_executor = concurrent.futures.ThreadPoolExecutor(max_workers=min(128, remaining_total), thread_name_prefix="qmdict-vi-synthesis")
            writer_workers = max(1, min(int(QMDICT_WORD_AUDIO_WRITER_WORKERS or 8), remaining_total))
            writer_executor = concurrent.futures.ThreadPoolExecutor(max_workers=writer_workers, thread_name_prefix="qmdict-vi-writer")
            result_buffer_limit = max(writer_workers, int(QMDICT_WORD_AUDIO_RESULT_BUFFER or 128))
            synthesis_futures = {}
            writer_futures = {}
            next_index = 0

            def fill_meaning_audio_capacity() -> None:
                nonlocal next_index, worker_count
                desired = qmdict_bulk_audio_concurrency(len(missing_entries) - done)
                worker_count = desired
                while not qmdict_audio_refresh_cancel_requested(job_id) and len(synthesis_futures) < desired and next_index < len(missing_entries):
                    item = missing_entries[next_index]
                    next_index += 1
                    synthesis_futures[synthesis_executor.submit(synthesize_meaning, item)] = item
                with QMDICT_AUDIO_REFRESH_LOCK:
                    QMDICT_AUDIO_REFRESH_JOB.update(
                        {
                            "workers": desired,
                            "writers": writer_workers,
                            "writer_pending": len(writer_futures),
                            "result_buffer_limit": result_buffer_limit,
                        }
                    )

            def record_meaning_row(row: dict, key: str, meaning: str) -> None:
                nonlocal done, downloaded, cached, failed, snapshot
                status = clean(row.get("status")).lower()
                if status != "cancelled":
                    done += 1
                if status == "downloaded":
                    downloaded += 1
                elif status == "cached-late":
                    cached += 1
                elif status not in {"cancelled"}:
                    failed += 1
                report_rows.append(row)
                with QMDICT_AUDIO_REFRESH_LOCK:
                    QMDICT_AUDIO_REFRESH_JOB.update(
                        {
                            "done": resume_done_offset + done,
                            "cached": cached,
                            "downloaded": downloaded,
                            "failed": failed,
                            "session_done": resume_done_offset + done,
                            "session_downloaded": downloaded,
                            "session_failed": failed,
                            "writer_pending": len(writer_futures),
                            "last_key": key,
                            "last_meaning": meaning[:180],
                            "updated_at": utc_timestamp(),
                        }
                    )
                    snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
                if done == remaining_total or (status != "cancelled" and done % 50 == 0) or status in {"failed", "missing"}:
                    atomic_write_json(QMDICT_AUDIO_REFRESH_REPORT_FILE, {"version": 1, **snapshot, "session_mode": session_mode, "entries": session_entries, "requested_keys": report_requested_keys, "items": report_rows}, indent=2)
                    write_qmdict_audio_refresh_progress({"version": 1, **snapshot})

            fill_meaning_audio_capacity()
            try:
                while synthesis_futures or writer_futures:
                    if qmdict_audio_refresh_cancel_requested(job_id):
                        for future in synthesis_futures:
                            future.cancel()
                    ready_writers = {future for future in writer_futures if future.done()}
                    if not ready_writers and writer_futures and (len(writer_futures) >= result_buffer_limit or not synthesis_futures):
                        ready_writers, _pending = concurrent.futures.wait(writer_futures, timeout=1.0, return_when=concurrent.futures.FIRST_COMPLETED)
                    for future in ready_writers:
                        key, meaning = writer_futures.pop(future)
                        try:
                            row = future.result()
                        except concurrent.futures.CancelledError:
                            row = {"key": key, "meaning": meaning, "status": "cancelled"}
                        except Exception as exc:
                            row = {"key": key, "meaning": meaning, "status": "failed", "error": str(exc)}
                        record_meaning_row(row, key, meaning)
                    if synthesis_futures and len(writer_futures) < result_buffer_limit:
                        ready_synthesis, _pending = concurrent.futures.wait(synthesis_futures, timeout=0.05, return_when=concurrent.futures.FIRST_COMPLETED)
                        available_writer_slots = max(0, result_buffer_limit - len(writer_futures))
                        for future in list(ready_synthesis)[:available_writer_slots]:
                            key, meaning = synthesis_futures.pop(future)
                            try:
                                result = future.result()
                            except concurrent.futures.CancelledError:
                                result = {"row": {"key": key, "meaning": meaning, "status": "cancelled"}}
                            except Exception as exc:
                                result = {"row": {"key": key, "meaning": meaning, "status": "failed", "error": str(exc)}}
                            writer_futures[writer_executor.submit(persist_meaning, result)] = (key, meaning)
                            fill_meaning_audio_capacity()
                    elif not ready_writers:
                        time.sleep(0.01)
            finally:
                synthesis_executor.shutdown(wait=True, cancel_futures=True)
                writer_executor.shutdown(wait=True, cancel_futures=True)
        cancelled = qmdict_audio_refresh_cancel_requested(job_id)
        completed_at = utc_timestamp()
        with QMDICT_AUDIO_REFRESH_LOCK:
            QMDICT_AUDIO_REFRESH_JOB.update({"running": False, "phase": "cancelled" if cancelled else "complete", "message": "Vietnamese audio refresh cancelled." if cancelled else "Vietnamese audio refresh complete.", "completed_at": completed_at, "updated_at": completed_at})
            final_snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
        atomic_write_json(QMDICT_AUDIO_REFRESH_REPORT_FILE, {"version": 1, **final_snapshot, "session_mode": session_mode, "entries": session_entries, "requested_keys": report_requested_keys, "items": report_rows}, indent=2)
        write_qmdict_audio_refresh_progress({"version": 1, **final_snapshot})
        stt_debug_log("qmdict_audio_refresh_done", job_id=job_id, mode=mode, total=session_total, downloaded=downloaded, failed=failed, cancelled=cancelled)
    except Exception as exc:
        with QMDICT_AUDIO_REFRESH_LOCK:
            QMDICT_AUDIO_REFRESH_JOB.update({"running": False, "phase": "failed", "message": "Vietnamese audio refresh failed.", "updated_at": utc_timestamp(), "error": str(exc)})
            snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
        write_qmdict_audio_refresh_progress({"version": 1, **snapshot})
        stt_debug_log("qmdict_audio_refresh_failed", job_id=job_id, mode=mode, error=str(exc))


def start_qmdict_meaning_audio_refresh(keys: object = None, mode: str = "qmdict-missing") -> dict:
    clean_mode = clean(mode).strip().lower() or "missing"
    if clean_mode in {"qmdict-missing", "dashboard-vietnamese-sot-refresh", "missing-only"}:
        clean_mode = "missing"
    if clean_mode not in {"missing", "force", "resume"}:
        clean_mode = "missing"
    requested_keys = keys[:1000] if isinstance(keys, list) else None
    with QMDICT_AUDIO_REFRESH_LOCK:
        if QMDICT_AUDIO_REFRESH_JOB.get("running"):
            return {"started": False, "audio_refresh": dict(QMDICT_AUDIO_REFRESH_JOB)}
        job_id = uuid.uuid4().hex
        started_at = utc_timestamp()
        QMDICT_AUDIO_REFRESH_JOB.update(
            {
                "running": True,
                "job_id": job_id,
                "mode": clean_mode,
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
                "cancel_requested": False,
            }
        )
        snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
    if clean_mode != "resume":
        atomic_write_json(
            QMDICT_AUDIO_REFRESH_REPORT_FILE,
            {
                "version": 1,
                **snapshot,
                "session_mode": clean_mode,
                "entries": [],
                "requested_keys": requested_keys,
                "items": [],
            },
            indent=2,
        )
        write_qmdict_audio_refresh_progress({"version": 1, **snapshot})
    thread = threading.Thread(
        target=run_qmdict_meaning_audio_refresh_job,
        args=(job_id, requested_keys, clean_mode),
        name=f"qmdict-audio-refresh-{job_id[:8]}",
        daemon=True,
    )
    thread.start()
    if clean_mode == "resume":
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
    # Added 2026-07-31: a warmed in-process QmDict lookup is milliseconds faster
    # than sending an inflected/missing key through the heavy worker queue while
    # opening Space_V. Keep the worker fallback for cold or unavailable runtime.
    if bool(SERVER_STATE.get("qmdict_runtime_ready")):
        try:
            direct = qmdict_lookup_summary(text, surface)
            if isinstance(direct, dict) and direct:
                return direct
        except Exception:
            pass
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
