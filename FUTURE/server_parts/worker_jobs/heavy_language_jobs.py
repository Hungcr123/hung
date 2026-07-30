from __future__ import annotations

import re
import sys
import time
import os
import ctypes
import json
from pathlib import Path


WORKER_PARTS_ROOT = Path(__file__).resolve().parents[1]
FUTURE_ROOT = WORKER_PARTS_ROOT.parent
ROOT = FUTURE_ROOT.parent
PROGRAME_ROOT = ROOT.parent
WORKER_TRANSLATOR = None


def set_worker_process_status(role: str = "process-worker") -> None:
    label = re.sub(r"\s+", " ", str(role or "process-worker")).strip() or "process-worker"
    os.environ["FUTURE_SERVER2_PROCESS_ROLE"] = label
    os.environ["FUTURE_SERVER2_PROCESS_STATUS"] = f"Future Server 2 - {label}"
    if os.name != "nt":
        return
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(f"Future Server 2 - {label}")
    except Exception:
        pass


# Added 2026-07-01: gives process workers the same import roots as Server 2 without importing the server first.
def configure_worker_paths() -> None:
    set_worker_process_status("process-worker")
    for item in (str(ROOT), str(PROGRAME_ROOT), str(FUTURE_ROOT)):
        if item not in sys.path:
            sys.path.insert(0, item)


def worker_clean(value: object = "") -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\r", " ").replace("\n", " ")).strip()


def worker_notice_text(value: object = "", limit: int = 2200) -> str:
    text = worker_clean(value)
    return text[: max(1, int(limit or 2200))]


def worker_translation_compare_key(value: str) -> str:
    return re.sub(r"[\W_]+", "", str(value or "").lower(), flags=re.UNICODE)


VIETNAMESE_MARK_RE = re.compile(
    r"[ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]",
    re.I,
)


def worker_translation_result_is_usable(source: str, translated: str, dest: str = "en") -> bool:
    output = str(translated or "").strip()
    if not output:
        return False
    source_key = worker_translation_compare_key(source)
    output_key = worker_translation_compare_key(output)
    if source_key and output_key and source_key == output_key:
        return False
    target = worker_clean(dest).lower()
    if target == "en" and VIETNAMESE_MARK_RE.search(output):
        return False
    return True


# Added 2026-07-09: explains why a translate result was rejected before cache write.
def worker_translation_failure_reason(source: str, translated: str, dest: str = "en") -> str:
    output = str(translated or "").strip()
    if not output:
        return "empty_output"
    source_key = worker_translation_compare_key(source)
    output_key = worker_translation_compare_key(output)
    if source_key and output_key and source_key == output_key:
        return "same_as_source"
    target = worker_clean(dest).lower()
    if target == "en" and VIETNAMESE_MARK_RE.search(output):
        return "target_en_still_has_vietnamese_marks"
    return "unknown_invalid_output"


# Added 2026-07-09: records rejected translate output without letting bad results enter cache.
def log_worker_invalid_translation(
    source: str,
    translated: str,
    dest: str = "en",
    src: str = "auto",
    reason: str = "",
    result_source: str = "fresh",
) -> None:
    log_dir = Path(r"C:\QMLearn\logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": utc_timestamp(),
        "src": worker_clean(src),
        "dest": worker_clean(dest),
        "reason": worker_clean(reason),
        "result_source": worker_clean(result_source) or "fresh",
        "source": worker_notice_text(source, limit=4000),
        "translated": worker_notice_text(translated, limit=4000),
        "cached": worker_clean(result_source).lower() == "cache",
    }
    with (log_dir / "future_worker_translate_rejected.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


# Added 2026-07-09: caches only validated worker translations and logs cache-write failures.
def cache_worker_valid_translation(source: str, translated: str, dest: str = "en", src: str = "auto") -> None:
    configure_worker_paths()
    from module_main.Data_Input.Import import _google_translate_cache_set  # type: ignore

    try:
        _google_translate_cache_set(source, translated, dest=dest, src=src)
    except Exception as exc:
        log_dir = Path(r"C:\QMLearn\logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": utc_timestamp(),
            "src": worker_clean(src),
            "dest": worker_clean(dest),
            "error": worker_notice_text(exc, limit=1200),
            "source": worker_notice_text(source, limit=1200),
            "translated": worker_notice_text(translated, limit=1200),
        }
        with (log_dir / "future_worker_translate_cache_error.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


# Added 2026-07-09: reads worker translate cache only when the cached text still passes validation.
def get_worker_valid_cached_translation(source: str, dest: str = "en", src: str = "auto") -> str | None:
    configure_worker_paths()
    from module_main.Data_Input.Import import _google_translate_cache_delete, _google_translate_cache_get  # type: ignore

    cached = _google_translate_cache_get(source, dest=dest, src=src)
    if cached is None:
        return None
    cached_text = worker_notice_text(cached, limit=2200)
    if worker_translation_result_is_usable(source, cached_text, dest):
        return cached_text
    reason = worker_translation_failure_reason(source, cached_text, dest)
    log_worker_invalid_translation(source, cached_text, dest=dest, src=src, reason=reason, result_source="cache")
    _google_translate_cache_delete(source, dest=dest, src=src)
    return None


def worker_translator():
    global WORKER_TRANSLATOR
    if WORKER_TRANSLATOR is None:
        configure_worker_paths()
        from module_main.Data_Input.Import import Translator  # type: ignore

        WORKER_TRANSLATOR = Translator()
    return WORKER_TRANSLATOR


# Added 2026-07-01: executes one Translator attempt inside the translate process pool.
def translate_text_once_worker(text: str, dest: str = "en", src: str = "auto", limit: int = 2200, force_refresh: bool = False) -> str:
    source = str(text or "").strip()
    if not source:
        return ""
    if not bool(force_refresh):
        cached = get_worker_valid_cached_translation(source, dest=dest, src=src)
        if cached is not None:
            return worker_notice_text(cached, limit=max(1, int(limit or 2200)))
    result = worker_translator().translate(
        source,
        dest=dest,
        src=src,
        force_refresh=True,
        write_cache=False,
    )
    translated = worker_notice_text(getattr(result, "text", "") or "", limit=max(1, int(limit or 2200)))
    if not worker_translation_result_is_usable(source, translated, dest):
        reason = worker_translation_failure_reason(source, translated, dest)
        log_worker_invalid_translation(source, translated, dest=dest, src=src, reason=reason, result_source="fresh")
        raise RuntimeError("Ket qua dich khong dung ngon ngu dich.")
    cache_worker_valid_translation(source, translated, dest=dest, src=src)
    return translated

# Added 2026-07-14: returns cache/fresh source metadata so worker dashboards can show where translate results came from.
def translate_text_once_worker_with_meta(text: str, dest: str = "en", src: str = "auto", limit: int = 2200, force_refresh: bool = False) -> dict:
    source = str(text or "").strip()
    if not source:
        return {"text": "", "source": "empty", "engine": "googletrans/http", "cached": False, "src": src, "dest": dest}
    if not bool(force_refresh):
        cached = get_worker_valid_cached_translation(source, dest=dest, src=src)
        if cached is not None:
            return {
                "text": worker_notice_text(cached, limit=max(1, int(limit or 2200))),
                "source": "cache",
                "engine": "googletrans/http",
                "cached": True,
                "src": src,
                "dest": dest,
            }
    translated = translate_text_once_worker(source, dest=dest, src=src, limit=limit, force_refresh=True)
    return {
        "text": translated,
        "source": "fresh",
        "engine": "googletrans/http",
        "cached": False,
        "src": src,
        "dest": dest,
    }


def _chat_audio_timing_payload(builder, source: str, voice: str, audio_bytes: bytes, mime: str) -> dict:
    analyzed = builder.analyze_sentence(source)
    tokens = builder.sentence_spans(source, analyzed, voice)
    duration_ms = builder.audio_duration_ms(audio_bytes, mime)
    if duration_ms <= 0:
        duration_ms = builder.estimate_duration_ms(source, tokens)
    timings = builder.build_audio_guided_timings(tokens, duration_ms, audio_bytes) or builder.build_timings(tokens, duration_ms)
    timing_tokens = []
    for index, token in enumerate(tokens):
        row = {
            "t": worker_clean(token.get("t") or token.get("text")),
            "s": int(token.get("s", index) or index),
            "e": int(token.get("e", index + 1) or (index + 1)),
        }
        ipa = worker_clean(token.get("i") or token.get("ipa"))
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


# Added 2026-07-01: executes Kokoro/SOT/Edge voice synthesis inside the voice process pool.
def synthesize_message_audio_worker(text: str, voice_key: str) -> dict:
    configure_worker_paths()
    import future_lesson_builder_gui as builder  # type: ignore

    source = str(text or "").strip()
    voice = worker_clean(voice_key)
    if not source:
        raise RuntimeError("Tin nhan dang trong.")
    if not voice:
        raise RuntimeError("Chua chon voice.")
    audio_bytes, mime = builder.synthesize_embedded_audio(source, voice, lambda _message: None)
    voice_label = builder.embedded_voice_label(voice)
    audio_path = builder.write_server_sound_asset(f"chat-{voice}-{source[:36]}", audio_bytes, mime)
    timing_payload = _chat_audio_timing_payload(builder, source, voice, audio_bytes, mime)
    normalized_voice = builder.normalize_audio_voice_key(voice) or voice
    audio_payload = {
        "path": audio_path,
        "mime": mime,
        "voice": normalized_voice,
        "label": voice_label,
    }
    audio_payload.update(timing_payload)
    return {
        "audio_path": audio_path,
        "audio_mime": mime,
        "voice": normalized_voice,
        "voice_label": voice_label,
        **timing_payload,
        "audio": audio_payload,
    }


# Added 2026-07-10: primes Vietnamese chat voice cache so first real message avoids cold Kokoro VI setup.
def warm_vietnamese_voice_audio_cache(builder) -> dict:
    sample_text = "Xin chao."
    voices = [
        "edge:vi-VN-NamMinhNeural",
        "edge:vi-VN-HoaiMyNeural",
    ]
    warm_all_kokoro = worker_clean(os.environ.get("FUTURE_WARM_ALL_KOKORO_VI", "")).lower() in {"1", "true", "yes", "on"}
    warm_some_kokoro = [
        worker_clean(item)
        for item in worker_clean(os.environ.get("FUTURE_WARM_KOKORO_VI", "")).split(",")
        if worker_clean(item)
    ]
    if warm_all_kokoro:
        try:
            for _label, key in list(builder.kokoro_vietnamese_voice_specs() or []):
                clean_key = worker_clean(key)
                if clean_key and clean_key not in voices:
                    voices.append(clean_key)
        except Exception:
            pass
    else:
        for key in warm_some_kokoro:
            clean_key = key if key.lower().startswith("kokoro_vi:") else f"kokoro_vi:{key}"
            if clean_key not in voices:
                voices.append(clean_key)
    warmed = []
    failed = []
    for voice in voices:
        started = time.time()
        try:
            if voice.lower().startswith("kokoro_vi:") and worker_clean(os.environ.get("FUTURE_KOKORO_VI_IN_PROCESS", "")).lower() in {"1", "true", "yes", "on", "warm"}:
                try:
                    _mime, extension = builder.audio_mime_for_voice(voice)
                    cache_path = builder.TTS_CACHE_DIR / f"{builder.voice_cache_key(sample_text, voice)}.{extension}"
                    if cache_path.is_file():
                        cache_path.unlink()
                except Exception:
                    pass
            audio_bytes, mime = builder.synthesize_embedded_audio(sample_text, voice, lambda _message: None)
            warmed.append({
                "voice": voice,
                "bytes": len(audio_bytes or b""),
                "mime": mime,
                "ms": int((time.time() - started) * 1000),
            })
        except Exception as exc:
            failed.append({"voice": voice, "error": worker_notice_text(exc, limit=300)})
    return {"voices": len(voices), "warmed": warmed, "failed": failed}

def _server_app():
    configure_worker_paths()
    from FUTURE import server_app  # type: ignore

    return server_app


# Added 2026-07-01: isolates heavy QmDict word/phrase scans from the main Server 2 process.
def qmdict_vocabulary_stats_worker(text: str = "", username: str = "", learned_keys: object = None) -> dict:
    app = _server_app()
    app.QMDICT_VOCAB_STATS_WORKER_ACTIVE = True
    try:
        # Updated 2026-07-22: use the authoritative main-process registry
        # snapshot instead of a stale per-process SQLite/RAM cache.
        return app.vocabulary_stats_for_text(text, username, learned_keys)
    finally:
        app.QMDICT_VOCAB_STATS_WORKER_ACTIVE = False


def qmdict_lookup_summary_worker(word: object = "", surface: str = "") -> dict:
    app = _server_app()
    return app.qmdict_lookup_summary(word, surface)


# Added 2026-07-01: isolates IPA generation and qmdict-backed phonetic lookup from request threads.
def phonetic_ipa_entry_worker(term: object = "", generate: bool = True) -> dict:
    app = _server_app()
    return app.get_or_create_phonetic_ipa(term, generate=generate)


def phonetic_ipa_map_worker(terms: object = None, generate_missing: bool = False, schedule_missing: bool = False) -> dict:
    app = _server_app()
    return app.phonetic_ipa_map_for_terms(terms, generate_missing=generate_missing, schedule_missing=schedule_missing)


# Added 2026-07-01: runs spaCy/QMWrite token analysis in the spaCy process pool.
def speech_training_token_analysis_worker(expected_text: str, expected_words: list[str]) -> tuple[list[dict], dict]:
    app = _server_app()
    return app.speech_training_token_analysis(expected_text, expected_words)


# Added 2026-07-01: primes child process imports/caches so heavy workers stay hot in RAM.
def warm_language_worker(kind: str = "") -> dict:
    configure_worker_paths()
    key = worker_clean(kind).lower()
    started = time.time()
    if key == "translate":
        # Added 2026-07-09: primes the exact vi->en path Ghost AI uses before real learner jobs arrive.
        sample = "chúng tôi muốn đi chơi ở đà lạt"
        translated = translate_text_once_worker(sample, dest="en", src="vi", limit=240)
        if not worker_translation_result_is_usable(sample, translated, "en"):
            raise RuntimeError("Translate warm smoke failed.")
        return {"kind": key, "ok": True, "sample": translated[:120], "ms": int((time.time() - started) * 1000)}
    elif key == "voice":
        import future_lesson_builder_gui as builder  # type: ignore

        kokoro_files = {}
        try:
            list(builder.people_voice_specs() or [])
        except Exception:
            pass
        try:
            list(builder.edge_vietnamese_voice_specs(force_refresh=False) or [])
            list(builder.kokoro_vietnamese_voice_specs() or [])
        except Exception:
            pass
        if worker_clean(os.environ.get("FUTURE_PREPARE_KOKORO_VI_FILES", "1")).lower() not in {"0", "false", "no", "off"}:
            try:
                kokoro_files = builder.ensure_kokoro_vietnamese_model_files(download=True, log=lambda _message: None)
            except Exception as exc:
                kokoro_files = {"ready": False, "error": worker_notice_text(exc, limit=500)}
        return {"kind": key, "ok": True, "kokoro_vi_files": kokoro_files, "ms": int((time.time() - started) * 1000)}
    elif key == "voice-model":
        import future_lesson_builder_gui as builder  # type: ignore

        audio_bytes = b""
        vi_warm = {}
        if worker_clean(os.environ.get("FUTURE_WARM_KOKORO_EN", "")).lower() in {"1", "true", "yes", "on"}:
            try:
                audio_bytes, _mime = builder.synthesize_embedded_audio("Warm.", "kokoro:am_adam", lambda _message: None)
            except Exception:
                audio_bytes = b""
        try:
            vi_warm = warm_vietnamese_voice_audio_cache(builder)
        except Exception as exc:
            vi_warm = {"error": worker_notice_text(exc, limit=500)}
        return {"kind": key, "ok": True, "bytes": len(audio_bytes or b""), "vi": vi_warm, "ms": int((time.time() - started) * 1000)}
    elif key == "qmdict":
        app = _server_app()
        try:
            _runtime, qmdict = app.qmdict_runtime_and_dict()
            entries = len(qmdict) if isinstance(qmdict, dict) else 0
        except Exception:
            entries = 0
        return {"kind": key, "ok": True, "entries": entries, "ms": int((time.time() - started) * 1000)}
    elif key == "phonetic":
        app = _server_app()
        try:
            cache = app.get_phonetic_ipa_cache()
            entries = len(cache.get("items") or {}) if isinstance(cache, dict) else 0
        except Exception:
            entries = 0
        return {"kind": key, "ok": True, "entries": entries, "ms": int((time.time() - started) * 1000)}
    elif key == "spacy":
        configure_worker_paths()
        try:
            from module_main.QMWrite.ScoringDef import analyze_sentence_data  # type: ignore

            analyze_sentence_data("This is a warm worker sentence.", {})
        except Exception:
            pass
    return {"kind": key or "worker", "ok": True, "ms": int((time.time() - started) * 1000)}
