# Loaded by FUTURE.server_parts.06_process_frontend_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

ZIPFORMER_VI_MODEL_DIR = Path(
    clean(os.environ.get("FUTURE_ZIPFORMER_VI_MODEL_DIR", ""))
    or r"C:\programe\sherpa_onnx_dashboard\models\sherpa-onnx-zipformer-vi-30M-int8-2026-02-09"
)
ZIPFORMER_VI_SITE_PACKAGES = Path(
    clean(os.environ.get("FUTURE_ZIPFORMER_VI_SITE_PACKAGES", ""))
    or r"C:\programe\sherpa_onnx_dashboard\.venv\Lib\site-packages"
)
ZIPFORMER_VI_SAMPLE_RATE = 16000
ZIPFORMER_VI_CACHE = {"obj": None, "model_dir": ""}
ZIPFORMER_VI_LOCK = threading.RLock()

def cpu_thread_count() -> int:
    raw = clean(os.environ.get("FUTURE_WHISPER_CPU_THREADS", ""))
    if raw.isdigit():
        return max(1, min(8, int(raw)))
    return max(1, min(4, int(os.cpu_count() or 2) // 2 or 1))


def load_whisper_model(model_ref: str, device: str = "cpu", compute_type: str = "int8"):
    configure_paths()
    from faster_whisper import WhisperModel

    normalized_ref = str(model_ref or "").strip()
    normalized_device = clean(device).lower() or "cpu"
    normalized_compute = clean(compute_type).lower() or "int8"
    if (
        MODEL_CACHE.get("obj") is not None
        and MODEL_CACHE.get("model_ref") == normalized_ref
        and MODEL_CACHE.get("device") == normalized_device
        and MODEL_CACHE.get("compute_type") == normalized_compute
    ):
        stt_debug_log("model_cache_hit", model_ref=normalized_ref, device=normalized_device, compute_type=normalized_compute)
        return MODEL_CACHE["obj"]
    MODEL_CACHE.update({"model_ref": "", "device": "", "compute_type": "", "obj": None})
    kwargs = {"device": normalized_device, "compute_type": normalized_compute}
    if normalized_device == "cpu":
        kwargs.update({"cpu_threads": cpu_thread_count(), "num_workers": 1})
    stt_debug_log("model_load_begin", model_ref=normalized_ref, device=normalized_device, compute_type=normalized_compute, kwargs=kwargs)
    model = WhisperModel(normalized_ref, **kwargs)
    stt_debug_log("model_load_done", model_ref=normalized_ref, device=normalized_device, compute_type=normalized_compute)
    MODEL_CACHE.update(
        {
            "model_ref": normalized_ref,
            "device": normalized_device,
            "compute_type": normalized_compute,
            "obj": model,
        }
    )
    return model


def transcribe_audio(audio_path: str, model_name: str, language: str) -> dict:
    model_ref = resolve_model_path(model_name)
    try:
        audio_size = Path(audio_path).stat().st_size
    except Exception:
        audio_size = 0
    stt_debug_log("transcribe_begin", audio_path=audio_path, audio_size=audio_size, model_name=model_name, model_ref=model_ref, language=language)

    def _collect_transcription(active_model):
        stt_debug_log("transcribe_model_call_begin", audio_path=audio_path)
        segments, _info = active_model.transcribe(audio_path, language=language, vad_filter=False, word_timestamps=True)
        stt_debug_log("transcribe_segments_received", audio_path=audio_path)
        collected_parts = []
        collected_words = []
        for segment in list(segments or []):
            text = clean(getattr(segment, "text", ""))
            if text:
                collected_parts.append(text)
            for word in list(getattr(segment, "words", []) or []):
                word_text = clean(getattr(word, "word", ""))
                if not word_text:
                    continue
                try:
                    start_ms = max(0.0, float(getattr(word, "start", 0.0) or 0.0) * 1000.0)
                except Exception:
                    start_ms = 0.0
                try:
                    end_ms = max(start_ms, float(getattr(word, "end", 0.0) or 0.0) * 1000.0)
                except Exception:
                    end_ms = start_ms
                collected_words.append({"word": word_text, "start_ms": round(start_ms, 2), "end_ms": round(end_ms, 2)})
        return collected_parts, collected_words

    with MODEL_LOCK:
        SERVER_STATE.update({"loading": True, "last_error": ""})
        stt_debug_log("transcribe_model_lock_acquired", audio_path=audio_path)
        if MODEL_CACHE.get("obj") is None and not SERVER_STATE.get("lazy_model_load"):
            SERVER_STATE.update({"loading": False, "ready": False, "last_error": "Whisper model is not preloaded."})
            stt_debug_log("transcribe_blocked_model_not_preloaded", audio_path=audio_path, model_ref=model_ref)
            raise RuntimeError("Whisper model is not preloaded. Restart future_whisper_server.py and wait until it says Future Whisper ready.")
        model = load_whisper_model(model_ref, "cpu", "int8")
        try:
            parts, words = _collect_transcription(model)
        except Exception as exc:
            if clean(MODEL_CACHE.get("device", "")).lower() != "cuda":
                raise
            stt_debug_log("transcribe_cuda_failed_retry_cpu", audio_path=audio_path, error=str(exc), traceback=traceback.format_exc())
            MODEL_CACHE.update({"model_ref": "", "device": "", "compute_type": "", "obj": None})
            model = load_whisper_model(model_ref, "cpu", "int8")
            parts, words = _collect_transcription(model)
    stt_debug_log("transcribe_done", audio_path=audio_path, text=clean(" ".join(parts)), words=len(words))
    SERVER_STATE.update(
        {
            "model_name": model_name,
            "model_ref": model_ref,
            "language": language,
            "device": "cpu",
            "compute_type": "int8",
            "ready": True,
            "loading": False,
            "last_error": "",
        }
    )
    return {"text": clean(" ".join(parts)), "words": words}


def _zipformer_vi_required_files(model_dir: Path) -> list[Path]:
    return [
        model_dir / "encoder.int8.onnx",
        model_dir / "decoder.onnx",
        model_dir / "joiner.int8.onnx",
        model_dir / "tokens.txt",
    ]


def _ensure_zipformer_vi_import_path() -> None:
    if ZIPFORMER_VI_SITE_PACKAGES.is_dir():
        path = str(ZIPFORMER_VI_SITE_PACKAGES)
        if path not in sys.path:
            sys.path.insert(0, path)


def load_zipformer_vi_recognizer():
    model_dir = ZIPFORMER_VI_MODEL_DIR
    missing = [str(item) for item in _zipformer_vi_required_files(model_dir) if not item.is_file()]
    if missing:
        raise RuntimeError("Vietnamese Zipformer model missing: " + " | ".join(missing))
    _ensure_zipformer_vi_import_path()
    import sherpa_onnx

    with ZIPFORMER_VI_LOCK:
        cached = ZIPFORMER_VI_CACHE.get("obj")
        if cached is not None and ZIPFORMER_VI_CACHE.get("model_dir") == str(model_dir):
            stt_debug_log("zipformer_vi_cache_hit", model_dir=str(model_dir))
            return cached
        stt_debug_log("zipformer_vi_load_begin", model_dir=str(model_dir))
        recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(model_dir / "encoder.int8.onnx"),
            decoder=str(model_dir / "decoder.onnx"),
            joiner=str(model_dir / "joiner.int8.onnx"),
            tokens=str(model_dir / "tokens.txt"),
            num_threads=2,
            sample_rate=ZIPFORMER_VI_SAMPLE_RATE,
            feature_dim=80,
            decoding_method="greedy_search",
            provider="cpu",
            model_type="transducer",
            debug=False,
        )
        ZIPFORMER_VI_CACHE.update({"obj": recognizer, "model_dir": str(model_dir)})
        stt_debug_log("zipformer_vi_load_done", model_dir=str(model_dir))
        return recognizer


def _read_zipformer_vi_audio(audio_path: str) -> tuple[object, int]:
    import numpy as np
    import soundfile as sf

    try:
        audio, sample_rate = sf.read(audio_path, dtype="float32", always_2d=True)
    except Exception:
        configure_paths()
        converted_path = Path(tempfile.gettempdir()) / f"future_zipformer_vi_{uuid.uuid4().hex}.wav"
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(audio_path),
            "-ac",
            "1",
            "-ar",
            str(ZIPFORMER_VI_SAMPLE_RATE),
            str(converted_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **subprocess_hidden_kwargs())
        audio, sample_rate = sf.read(str(converted_path), dtype="float32", always_2d=True)
        try:
            converted_path.unlink(missing_ok=True)
        except Exception:
            pass
    if audio.size <= 0:
        return np.zeros(0, dtype=np.float32), int(sample_rate or ZIPFORMER_VI_SAMPLE_RATE)
    samples = audio[:, 0] if audio.shape[1] == 1 else audio.mean(axis=1)
    samples = np.ascontiguousarray(samples, dtype=np.float32)
    source_rate = int(sample_rate or ZIPFORMER_VI_SAMPLE_RATE)
    if source_rate != ZIPFORMER_VI_SAMPLE_RATE and len(samples) > 1:
        duration = float(len(samples)) / float(max(1, source_rate))
        target_len = max(1, int(round(duration * ZIPFORMER_VI_SAMPLE_RATE)))
        source_x = np.linspace(0.0, duration, num=len(samples), endpoint=False)
        target_x = np.linspace(0.0, duration, num=target_len, endpoint=False)
        samples = np.ascontiguousarray(np.interp(target_x, source_x, samples), dtype=np.float32)
        source_rate = ZIPFORMER_VI_SAMPLE_RATE
    return samples, source_rate


def transcribe_zipformer_vi_audio(audio_path: str) -> dict:
    import numpy as np

    started_at = time.perf_counter()
    try:
        audio_size = Path(audio_path).stat().st_size
    except Exception:
        audio_size = 0
    stt_debug_log("zipformer_vi_transcribe_begin", audio_path=audio_path, audio_size=audio_size)
    samples, sample_rate = _read_zipformer_vi_audio(audio_path)
    samples = np.ascontiguousarray(samples, dtype=np.float32)
    duration = float(len(samples)) / float(max(1, int(sample_rate or ZIPFORMER_VI_SAMPLE_RATE)))
    if len(samples) <= 0 or duration <= 0:
        return {
            "text": "",
            "words": [],
            "language": "vi",
            "model": "zipformer-vi-30M-int8",
            "model_ref": str(ZIPFORMER_VI_MODEL_DIR),
            "engine": "sherpa-onnx-zipformer-vi-int8",
            "provider": "local_cpu",
            "duration": 0,
            "decode_ms": 0,
            "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
            "rtf": 0,
        }
    recognizer = load_zipformer_vi_recognizer()
    decode_started_at = time.perf_counter()
    with ZIPFORMER_VI_LOCK:
        stream = recognizer.create_stream()
        stream.accept_waveform(int(sample_rate), samples)
        recognizer.decode_stream(stream)
        text = clean(getattr(stream.result, "text", "")).lower()
    decode_ms = int((time.perf_counter() - decode_started_at) * 1000)
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    result = {
        "text": text,
        "words": [],
        "language": "vi",
        "model": "zipformer-vi-30M-int8",
        "model_ref": str(ZIPFORMER_VI_MODEL_DIR),
        "engine": "sherpa-onnx-zipformer-vi-int8",
        "provider": "local_cpu",
        "duration": round(duration, 3),
        "decode_ms": decode_ms,
        "elapsed_ms": elapsed_ms,
        "rtf": round((decode_ms / 1000.0) / duration, 3) if duration > 0 else 0,
    }
    SERVER_STATE.update(
        {
            "zipformer_vi_ready": True,
            "zipformer_vi_model_ref": str(ZIPFORMER_VI_MODEL_DIR),
            "zipformer_vi_last_elapsed_ms": elapsed_ms,
            "zipformer_vi_last_error": "",
        }
    )
    stt_debug_log("zipformer_vi_transcribe_done", audio_path=audio_path, text=text, elapsed_ms=elapsed_ms, rtf=result["rtf"])
    return result


def stt_queue_worker() -> None:
    while True:
        job = STT_QUEUE.get()
        try:
            if job.get("cancelled"):
                with STT_QUEUE_LOCK:
                    SERVER_STATE.update({"queue_pending": STT_QUEUE.qsize()})
                continue
            started_at = time.time()
            with STT_QUEUE_LOCK:
                SERVER_STATE.update(
                    {
                        "queue_pending": STT_QUEUE.qsize(),
                        "queue_active": True,
                        "queue_active_id": job["id"],
                        "queue_active_started_at": started_at,
                        "loading": True,
                        "last_error": "",
                    }
            )
            print(f"STT queue start: {job['id']} | pending={STT_QUEUE.qsize()}", flush=True)
            stt_debug_log("queue_start", job_id=job["id"], pending=STT_QUEUE.qsize(), audio_path=job.get("audio_path", ""), model_name=job.get("model_name", ""), language=job.get("language", ""))
            try:
                job["result"] = transcribe_audio(job["audio_path"], job["model_name"], job["language"])
            except Exception as exc:
                job["error"] = str(exc)
                stt_debug_log("queue_error", job_id=job["id"], error=str(exc), traceback=traceback.format_exc())
            finished_at = time.time()
            wait_ms = int(max(0.0, started_at - job["queued_at"]) * 1000)
            process_ms = int(max(0.0, finished_at - started_at) * 1000)
            job["wait_ms"] = wait_ms
            job["process_ms"] = process_ms
            with STT_QUEUE_LOCK:
                if job.get("error"):
                    SERVER_STATE["queue_failed"] = int(SERVER_STATE.get("queue_failed", 0)) + 1
                    SERVER_STATE.update({"last_error": job["error"]})
                else:
                    SERVER_STATE["queue_completed"] = int(SERVER_STATE.get("queue_completed", 0)) + 1
                    SERVER_STATE.update({"last_error": ""})
                SERVER_STATE.update(
                    {
                        "queue_pending": STT_QUEUE.qsize(),
                        "queue_active": False,
                        "queue_active_id": "",
                        "queue_active_started_at": 0,
                        "queue_last_wait_ms": wait_ms,
                        "queue_last_process_ms": process_ms,
                        "queue_last_completed_at": finished_at,
                        "loading": False,
                    }
            )
            print(f"STT queue done: {job['id']} | wait={wait_ms}ms | run={process_ms}ms", flush=True)
            stt_debug_log("queue_done", job_id=job["id"], wait_ms=wait_ms, process_ms=process_ms, error=job.get("error", ""))
        finally:
            try:
                job["done"].set()
            finally:
                STT_QUEUE.task_done()


def ensure_stt_queue_worker() -> threading.Thread:
    global STT_WORKER_THREAD
    with STT_QUEUE_LOCK:
        if STT_WORKER_THREAD and STT_WORKER_THREAD.is_alive():
            return STT_WORKER_THREAD
        STT_WORKER_THREAD = threading.Thread(target=stt_queue_worker, name="future-whisper-stt-queue", daemon=True)
        STT_WORKER_THREAD.start()
        return STT_WORKER_THREAD


def submit_transcription_job(audio_path: str, model_name: str, language: str) -> dict:
    ensure_stt_queue_worker()
    job_id = uuid.uuid4().hex[:12]
    done = threading.Event()
    queued_at = time.time()
    with STT_QUEUE_LOCK:
        queue_position = STT_QUEUE.qsize() + (1 if SERVER_STATE.get("queue_active") else 0) + 1
        SERVER_STATE["queue_total"] = int(SERVER_STATE.get("queue_total", 0)) + 1
        SERVER_STATE.update({"queue_pending": STT_QUEUE.qsize() + 1, "last_error": ""})
    job = {
        "id": job_id,
        "audio_path": audio_path,
        "model_name": model_name,
        "language": language,
        "queued_at": queued_at,
        "queue_position": queue_position,
        "done": done,
        "cancelled": False,
        "result": None,
        "error": "",
        "wait_ms": 0,
        "process_ms": 0,
    }
    STT_QUEUE.put(job)
    print(f"STT queue add: {job_id} | position={queue_position}", flush=True)
    stt_debug_log("queue_add", job_id=job_id, position=queue_position, audio_path=audio_path, model_name=model_name, language=language)
    timeout_seconds = max(0, int(STT_JOB_TIMEOUT_SECONDS or 0))
    completed = done.wait(timeout_seconds) if timeout_seconds > 0 else (done.wait() or True)
    if not completed:
        job["cancelled"] = True
        with STT_QUEUE_LOCK:
            SERVER_STATE["queue_timeout"] = int(SERVER_STATE.get("queue_timeout", 0)) + 1
            SERVER_STATE.update({"queue_pending": STT_QUEUE.qsize()})
        stt_debug_log("queue_timeout", job_id=job_id, timeout_seconds=timeout_seconds)
        raise TimeoutError(f"STT queue timeout after {timeout_seconds} seconds.")
    if job.get("error"):
        stt_debug_log("queue_raise_error", job_id=job_id, error=job.get("error", ""))
        raise RuntimeError(job["error"])
    result = dict(job.get("result") or {})
    result.update(
        {
            "job_id": job_id,
            "queue_position": queue_position,
            "queue_wait_ms": int(job.get("wait_ms", 0) or 0),
            "queue_process_ms": int(job.get("process_ms", 0) or 0),
        }
    )
    return result


def preload_model(model_name: str, language: str) -> None:
    model_ref = resolve_model_path(model_name)
    with MODEL_LOCK:
        load_whisper_model(model_ref, "cpu", "int8")
    SERVER_STATE.update(
        {
            "model_name": model_name,
            "model_ref": model_ref,
            "language": language,
            "device": "cpu",
            "compute_type": "int8",
            "ready": True,
            "loading": False,
            "last_error": "",
        }
    )


def preload_model_background(model_name: str, language: str) -> threading.Thread:
    def runner() -> None:
        SERVER_STATE.update(
            {
                "model_name": model_name,
                "language": language,
                "ready": False,
                "loading": True,
                "preload_started_at": time.time(),
                "preload_finished_at": 0,
                "last_error": "",
            }
        )
        try:
            preload_model(model_name, language)
            SERVER_STATE.update({"loading": False, "preload_finished_at": time.time(), "last_error": ""})
            print(f"Future Whisper ready: {SERVER_STATE['model_ref']}", flush=True)
        except Exception as exc:
            SERVER_STATE.update({"ready": False, "loading": False, "preload_finished_at": time.time(), "last_error": str(exc)})
            print(f"Future Whisper preload skipped: {exc}", flush=True)

    thread = threading.Thread(target=runner, name="future-whisper-preload", daemon=True)
    thread.start()
    return thread


def preload_model_sync(model_name: str, language: str) -> bool:
    SERVER_STATE.update(
        {
            "model_name": model_name,
            "language": language,
            "ready": False,
            "loading": True,
            "preload_started_at": time.time(),
            "preload_finished_at": 0,
            "last_error": "",
        }
    )
    stt_debug_log("preload_sync_begin", model_name=model_name, language=language)
    try:
        preload_model(model_name, language)
        SERVER_STATE.update({"loading": False, "preload_finished_at": time.time(), "last_error": ""})
        print(f"Future Whisper ready: {SERVER_STATE['model_ref']}", flush=True)
        stt_debug_log("preload_sync_done", model_ref=SERVER_STATE.get("model_ref", ""))
        return True
    except Exception as exc:
        SERVER_STATE.update({"ready": False, "loading": False, "preload_finished_at": time.time(), "last_error": str(exc)})
        print(f"Future Whisper preload failed: {exc}", flush=True)
        stt_debug_log("preload_sync_failed", error=str(exc), traceback=traceback.format_exc())
        return False
