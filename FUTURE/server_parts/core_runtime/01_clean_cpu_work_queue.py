# Loaded by FUTURE.server_parts.01_core_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

# Added 2026-07-22: this helper is hot across every route; reuse the compiled whitespace pattern.
CLEAN_WHITESPACE_RE = re.compile(r"\s+")


def clean(value) -> str:
    return CLEAN_WHITESPACE_RE.sub(" ", str(value or "").replace("\r", " ").replace("\n", " ")).strip()


def bounded_env_int(name: str, default: int, minimum: int = 1, maximum: int = 128) -> int:
    raw = clean(os.environ.get(name, ""))
    try:
        value = int(raw)
    except Exception:
        value = int(default)
    return max(int(minimum), min(int(maximum), value))


class _FileTime(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


CPU_SAMPLE_LOCK = threading.RLock()
CPU_SAMPLE_STATE = {"at": 0.0, "idle": 0, "kernel": 0, "user": 0, "percent": 0.0}
WORKLOAD_CPU_HIGH_PERCENT = bounded_env_int("FUTURE_SERVER_QUEUE_CPU_PERCENT", 90, 45, 98)
CPU_GUARD_LOCK = threading.RLock()
CPU_GUARD_STATE = {"enabled": True, "threshold": WORKLOAD_CPU_HIGH_PERCENT}


def apply_cpu_guard_settings(enabled: object = True, threshold: object = WORKLOAD_CPU_HIGH_PERCENT) -> dict:
    try:
        percent = int(float(threshold))
    except Exception:
        percent = WORKLOAD_CPU_HIGH_PERCENT
    percent = max(45, min(98, percent))
    guard_enabled = truthy(enabled, True) if "truthy" in globals() else bool(enabled)
    with CPU_GUARD_LOCK:
        CPU_GUARD_STATE.update({"enabled": bool(guard_enabled), "threshold": percent})
        return dict(CPU_GUARD_STATE)


def cpu_guard_settings_snapshot() -> dict:
    with CPU_GUARD_LOCK:
        return dict(CPU_GUARD_STATE)


def _filetime_value(value: _FileTime) -> int:
    return (int(value.dwHighDateTime) << 32) + int(value.dwLowDateTime)


def current_system_cpu_percent() -> float:
    now = time.time()
    with CPU_SAMPLE_LOCK:
        if now - float(CPU_SAMPLE_STATE.get("at", 0.0) or 0.0) < 0.75:
            return float(CPU_SAMPLE_STATE.get("percent", 0.0) or 0.0)
        try:
            idle = _FileTime()
            kernel = _FileTime()
            user = _FileTime()
            ok = ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
            if not ok:
                return float(CPU_SAMPLE_STATE.get("percent", 0.0) or 0.0)
            idle_value = _filetime_value(idle)
            kernel_value = _filetime_value(kernel)
            user_value = _filetime_value(user)
            prev_idle = int(CPU_SAMPLE_STATE.get("idle", 0) or 0)
            prev_kernel = int(CPU_SAMPLE_STATE.get("kernel", 0) or 0)
            prev_user = int(CPU_SAMPLE_STATE.get("user", 0) or 0)
            if prev_kernel <= 0 or prev_user <= 0:
                percent = 0.0
            else:
                idle_delta = max(0, idle_value - prev_idle)
                total_delta = max(1, (kernel_value - prev_kernel) + (user_value - prev_user))
                percent = max(0.0, min(100.0, (1.0 - (idle_delta / float(total_delta))) * 100.0))
            CPU_SAMPLE_STATE.update({
                "at": now,
                "idle": idle_value,
                "kernel": kernel_value,
                "user": user_value,
                "percent": percent,
            })
            return percent
        except Exception:
            return float(CPU_SAMPLE_STATE.get("percent", 0.0) or 0.0)


class FutureWorkQueue:
    def __init__(
        self,
        name: str,
        label: str,
        max_workers: int,
        max_pending: int,
        timeout_seconds: int,
        throttle_workers: int = 1,
        cpu_threshold: int | None = None,
        cpu_guard: bool = True,
    ):
        self.name = clean(name) or "work"
        self.label = clean(label) or self.name
        self.max_workers = max(1, int(max_workers or 1))
        self.max_pending = max(0, int(max_pending or 0))
        self.timeout_seconds = max(5, int(timeout_seconds or 60))
        self.throttle_workers = max(1, min(self.max_workers, int(throttle_workers or 1)))
        self.cpu_threshold = int(cpu_threshold if cpu_threshold is not None else WORKLOAD_CPU_HIGH_PERCENT)
        self.cpu_guard = bool(cpu_guard)
        self.lock = threading.RLock()
        self.ticket = threading.BoundedSemaphore(self.max_workers + self.max_pending)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix=f"future-{self.name}")
        self.stats = {
            "name": self.name,
            "label": self.label,
            "max_workers": self.max_workers,
            "max_pending": self.max_pending,
            "throttle_workers": self.throttle_workers,
            "cpu_threshold": self.cpu_threshold,
            "pending": 0,
            "active": 0,
            "total": 0,
            "completed": 0,
            "failed": 0,
            "timeout": 0,
            "rejected": 0,
            "last_wait_ms": 0,
            "last_process_ms": 0,
            "last_label": "",
            "last_error": "",
            "last_completed_at": 0.0,
            "cpu_percent": 0.0,
            "cpu_guard_enabled": self.cpu_guard,
        }

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.stats)

    def _allowed_workers(self) -> int:
        cpu_percent = current_system_cpu_percent()
        guard = cpu_guard_settings_snapshot()
        guard_enabled = self.cpu_guard and bool(guard.get("enabled", True))
        threshold = int(guard.get("threshold", self.cpu_threshold) or self.cpu_threshold)
        with self.lock:
            self.stats["cpu_percent"] = round(cpu_percent, 1)
            self.stats["cpu_threshold"] = threshold
            self.stats["cpu_guard_enabled"] = guard_enabled
        return self.throttle_workers if guard_enabled and cpu_percent >= threshold else self.max_workers

    def _wait_for_cpu_slot(self) -> None:
        while True:
            with self.lock:
                active = int(self.stats.get("active", 0) or 0)
            if active < self._allowed_workers():
                return
            time.sleep(0.08 if active < self.max_workers else 0.16)

    def run(self, label: str, fn, timeout: int | None = None):
        job_label = clean(label)[:100] or self.label
        queued_at = time.time()
        if not self.ticket.acquire(blocking=False):
            with self.lock:
                self.stats["rejected"] = int(self.stats.get("rejected", 0) or 0) + 1
                self.stats["last_error"] = "queue_full"
            raise RuntimeError(f"{self.label} queue is busy. Please retry shortly.")
        with self.lock:
            self.stats["pending"] = int(self.stats.get("pending", 0) or 0) + 1
            self.stats["total"] = int(self.stats.get("total", 0) or 0) + 1
            self.stats["last_label"] = job_label
            self.stats["last_error"] = ""

        def wrapper():
            self._wait_for_cpu_slot()
            started_at = time.time()
            with self.lock:
                self.stats["pending"] = max(0, int(self.stats.get("pending", 0) or 0) - 1)
                self.stats["active"] = int(self.stats.get("active", 0) or 0) + 1
            ok = False
            error_text = ""
            try:
                result = fn()
                ok = True
                return result
            except Exception as exc:
                error_text = str(exc)
                raise
            finally:
                finished_at = time.time()
                with self.lock:
                    self.stats["active"] = max(0, int(self.stats.get("active", 0) or 0) - 1)
                    if ok:
                        self.stats["completed"] = int(self.stats.get("completed", 0) or 0) + 1
                        self.stats["last_error"] = ""
                    else:
                        self.stats["failed"] = int(self.stats.get("failed", 0) or 0) + 1
                        self.stats["last_error"] = clean(error_text)[:240]
                    self.stats["last_wait_ms"] = int(max(0.0, started_at - queued_at) * 1000)
                    self.stats["last_process_ms"] = int(max(0.0, finished_at - started_at) * 1000)
                    self.stats["last_completed_at"] = finished_at

        try:
            future = self.executor.submit(wrapper)
        except Exception:
            with self.lock:
                self.stats["pending"] = max(0, int(self.stats.get("pending", 0) or 0) - 1)
            self.ticket.release()
            raise

        future.add_done_callback(lambda _done: self.ticket.release())
        try:
            if timeout is not None and int(timeout) <= 0:
                return future.result()
            return future.result(timeout=max(1, int(timeout or self.timeout_seconds)))
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            with self.lock:
                self.stats["timeout"] = int(self.stats.get("timeout", 0) or 0) + 1
                self.stats["last_error"] = "timeout"
            raise RuntimeError(f"{self.label} queue timed out. Please retry shortly.") from exc


# Added 2026-07-01: runs heavy translate/voice work in child processes so request threads stay light.
class FutureProcessWorkQueue:
    def __init__(
        self,
        name: str,
        label: str,
        max_workers: int,
        max_pending: int,
        timeout_seconds: int,
    ):
        self.name = clean(name) or "process-work"
        self.label = clean(label) or self.name
        self.max_workers = max(1, int(max_workers or 1))
        self.max_pending = max(0, int(max_pending or 0))
        self.timeout_seconds = max(5, int(timeout_seconds or 60))
        self.lock = threading.RLock()
        self.ticket = threading.BoundedSemaphore(self.max_workers + self.max_pending)
        self.executor = None
        self.stats = {
            "name": self.name,
            "label": self.label,
            "kind": "process",
            "max_workers": self.max_workers,
            "max_pending": self.max_pending,
            "throttle_workers": self.max_workers,
            "cpu_threshold": 0,
            "pending": 0,
            "active": 0,
            "total": 0,
            "completed": 0,
            "failed": 0,
            "timeout": 0,
            "rejected": 0,
            "last_wait_ms": 0,
            "last_process_ms": 0,
            "last_label": "",
            "last_error": "",
            "last_completed_at": 0.0,
            "cpu_percent": 0.0,
            "cpu_guard_enabled": False,
        }

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.stats)

    def _executor(self):
        with self.lock:
            if self.executor is None:
                self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers)
            return self.executor

    def warm(self, label: str, fn, *args, timeout: int | None = None, count: int | None = None, **kwargs) -> list:
        job_label = clean(label)[:100] or f"{self.label} warm"
        with self.lock:
            self.stats["last_label"] = job_label
            self.stats["last_error"] = ""
        process_warm = globals().get("warm_process_worker_task")
        process_supported = globals().get("process_worker_task_supported")
        if callable(process_warm) and callable(process_supported) and process_supported(self.name, fn):
            try:
                kind = clean(args[0] if args else self.name) or self.name
                result = process_warm(self.name, kind, timeout=timeout or self.timeout_seconds)
                with self.lock:
                    self.stats["completed"] = int(self.stats.get("completed", 0) or 0) + 1
                    self.stats["last_completed_at"] = time.time()
                return [result]
            except Exception as exc:
                with self.lock:
                    self.stats["last_error"] = clean(exc)[:240]
                if "stt_debug_log" in globals():
                    stt_debug_log("persistent_process_worker_warm_fallback", queue=self.name, error=str(exc))
        executor = self._executor()
        warm_count = max(1, min(self.max_workers, int(count or self.max_workers)))
        futures = [executor.submit(fn, *args, **kwargs) for _index in range(warm_count)]
        results = []
        try:
            for future in futures:
                results.append(future.result(timeout=max(1, int(timeout or self.timeout_seconds))))
        except concurrent.futures.TimeoutError as exc:
            with self.lock:
                self.stats["timeout"] = int(self.stats.get("timeout", 0) or 0) + 1
                self.stats["last_error"] = "warm_timeout"
            raise RuntimeError(f"{self.label} warm timed out. Please retry shortly.") from exc
        except Exception as exc:
            with self.lock:
                self.stats["failed"] = int(self.stats.get("failed", 0) or 0) + 1
                self.stats["last_error"] = clean(exc)[:240]
            raise
        with self.lock:
            self.stats["completed"] = int(self.stats.get("completed", 0) or 0) + len(results)
            self.stats["last_completed_at"] = time.time()
        return results

    def run(self, label: str, fn, *args, timeout: int | None = None, **kwargs):
        job_label = clean(label)[:100] or self.label
        queued_at = time.time()
        if not self.ticket.acquire(blocking=False):
            with self.lock:
                self.stats["rejected"] = int(self.stats.get("rejected", 0) or 0) + 1
                self.stats["last_error"] = "queue_full"
            raise RuntimeError(f"{self.label} worker is busy. Please retry shortly.")
        with self.lock:
            self.stats["pending"] = int(self.stats.get("pending", 0) or 0) + 1
            self.stats["total"] = int(self.stats.get("total", 0) or 0) + 1
            self.stats["last_label"] = job_label
            self.stats["last_error"] = ""
        process_run = globals().get("run_process_worker_task")
        process_supported = globals().get("process_worker_task_supported")
        if callable(process_run) and callable(process_supported) and process_supported(self.name, fn):
            started_at = time.time()
            try:
                result = process_run(self.name, job_label, fn, args, kwargs, timeout=timeout or self.timeout_seconds)
                finished_at = time.time()
                with self.lock:
                    self.stats["pending"] = max(0, int(self.stats.get("pending", 0) or 0) - 1)
                    self.stats["completed"] = int(self.stats.get("completed", 0) or 0) + 1
                    self.stats["last_error"] = ""
                    self.stats["last_wait_ms"] = int(max(0.0, started_at - queued_at) * 1000)
                    self.stats["last_process_ms"] = int(max(0.0, finished_at - started_at) * 1000)
                    self.stats["last_completed_at"] = finished_at
                self.ticket.release()
                return result
            except Exception as exc:
                with self.lock:
                    self.stats["last_error"] = clean(exc)[:240]
                if "stt_debug_log" in globals():
                    stt_debug_log("persistent_process_worker_run_fallback", queue=self.name, label=job_label, error=str(exc))
        submitted_at = time.time()
        try:
            future = self._executor().submit(fn, *args, **kwargs)
        except Exception:
            with self.lock:
                self.stats["pending"] = max(0, int(self.stats.get("pending", 0) or 0) - 1)
            self.ticket.release()
            raise
        with self.lock:
            self.stats["pending"] = max(0, int(self.stats.get("pending", 0) or 0) - 1)
            self.stats["active"] = int(self.stats.get("active", 0) or 0) + 1
            self.stats["last_wait_ms"] = int(max(0.0, submitted_at - queued_at) * 1000)

        def finish(done_future) -> None:
            finished_at = time.time()
            error_text = ""
            ok = False
            try:
                done_future.result()
                ok = True
            except Exception as exc:
                error_text = str(exc)
            with self.lock:
                self.stats["active"] = max(0, int(self.stats.get("active", 0) or 0) - 1)
                if ok:
                    self.stats["completed"] = int(self.stats.get("completed", 0) or 0) + 1
                    self.stats["last_error"] = ""
                else:
                    self.stats["failed"] = int(self.stats.get("failed", 0) or 0) + 1
                    if error_text:
                        self.stats["last_error"] = clean(error_text)[:240]
                self.stats["last_process_ms"] = int(max(0.0, finished_at - submitted_at) * 1000)
                self.stats["last_completed_at"] = finished_at
            self.ticket.release()

        future.add_done_callback(finish)
        try:
            if timeout is not None and int(timeout) <= 0:
                return future.result()
            return future.result(timeout=max(1, int(timeout or self.timeout_seconds)))
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            with self.lock:
                self.stats["timeout"] = int(self.stats.get("timeout", 0) or 0) + 1
                self.stats["last_error"] = "timeout"
            raise RuntimeError(f"{self.label} worker timed out. Please retry shortly.") from exc


GEMINI_WORK_QUEUE = FutureWorkQueue(
    "ghost-ai",
    "Ghost AI",
    bounded_env_int("FUTURE_GEMINI_WORKERS", 1, 1, 4),
    bounded_env_int("FUTURE_GEMINI_PENDING", 24, 4, 80),
    bounded_env_int("FUTURE_GEMINI_TIMEOUT", 120, 30, 240),
    throttle_workers=1,
)
TRANSLATE_WORK_QUEUE = FutureProcessWorkQueue(
    "translate",
    "Translate",
    bounded_env_int("FUTURE_TRANSLATE_WORKERS", 3, 1, 6),
    bounded_env_int("FUTURE_TRANSLATE_PENDING", 96, 4, 240),
    bounded_env_int("FUTURE_TRANSLATE_TIMEOUT", 80, 20, 180),
)
VOICE_WORK_QUEUE = FutureProcessWorkQueue(
    "voice",
    "Voice",
    bounded_env_int("FUTURE_VOICE_WORKERS", 2, 1, 4),
    bounded_env_int("FUTURE_VOICE_PENDING", 96, 4, 240),
    bounded_env_int("FUTURE_VOICE_TIMEOUT", 180, 30, 300),
)
AI_QUESTION_VOICE_WORK_QUEUE = FutureProcessWorkQueue(
    "ai-question-voice",
    "AI Question Voice",
    bounded_env_int("FUTURE_AI_QUESTION_VOICE_WORKERS", 1, 1, 2),
    bounded_env_int("FUTURE_AI_QUESTION_VOICE_PENDING", 64, 4, 180),
    bounded_env_int("FUTURE_AI_QUESTION_VOICE_TIMEOUT", 240, 30, 420),
)
QMDICT_WORK_QUEUE = FutureProcessWorkQueue(
    "qmdict",
    "QmDict",
    bounded_env_int("FUTURE_QMDICT_WORKERS", 2, 1, 4),
    bounded_env_int("FUTURE_QMDICT_PENDING", 128, 8, 300),
    bounded_env_int("FUTURE_QMDICT_TIMEOUT", 90, 20, 240),
)
PHONETIC_WORK_QUEUE = FutureProcessWorkQueue(
    "phonetic",
    "Phonetic",
    bounded_env_int("FUTURE_PHONETIC_WORKERS", 2, 1, 4),
    bounded_env_int("FUTURE_PHONETIC_PENDING", 128, 8, 300),
    bounded_env_int("FUTURE_PHONETIC_TIMEOUT", 90, 20, 240),
)
SPACY_WORK_QUEUE = FutureProcessWorkQueue(
    "spacy",
    "spaCy",
    bounded_env_int("FUTURE_SPACY_WORKERS", 2, 1, 4),
    bounded_env_int("FUTURE_SPACY_PENDING", 96, 4, 240),
    bounded_env_int("FUTURE_SPACY_TIMEOUT", 90, 20, 240),
)
GHOST_EYE_WORK_QUEUE = FutureWorkQueue(
    "ghost-eye",
    "Ghost Eye",
    bounded_env_int("FUTURE_GHOST_EYE_WORKERS", 3, 1, 6),
    bounded_env_int("FUTURE_GHOST_EYE_PENDING", 36, 2, 120),
    bounded_env_int("FUTURE_GHOST_EYE_TIMEOUT", 160, 30, 300),
    throttle_workers=1,
)
PDF_RENDER_WORK_QUEUE = FutureWorkQueue(
    "pdf-render",
    "PDF render",
    bounded_env_int("FUTURE_PDF_RENDER_WORKERS", 4, 1, 8),
    bounded_env_int("FUTURE_PDF_RENDER_PENDING", 64, 4, 160),
    bounded_env_int("FUTURE_PDF_RENDER_TIMEOUT", 90, 20, 180),
    throttle_workers=1,
)
SERVER_WORK_QUEUES = {
    "translate": TRANSLATE_WORK_QUEUE,
    "voice": VOICE_WORK_QUEUE,
    "ai-question-voice": AI_QUESTION_VOICE_WORK_QUEUE,
    "qmdict": QMDICT_WORK_QUEUE,
    "phonetic": PHONETIC_WORK_QUEUE,
    "spacy": SPACY_WORK_QUEUE,
    "ghost_eye": GHOST_EYE_WORK_QUEUE,
    "pdf_render": PDF_RENDER_WORK_QUEUE,
}


# Added 2026-07-01: pre-spawns heavy process workers so their imports/caches stay hot in RAM.
def warm_future_process_workers_async(delay: float = 0.8) -> None:
    def worker() -> None:
        try:
            time.sleep(max(0.0, float(delay or 0.0)))
            from FUTURE.server_parts.worker_jobs.heavy_language_jobs import warm_language_worker

            specs = [
                ("translate", TRANSLATE_WORK_QUEUE),
                ("qmdict", QMDICT_WORK_QUEUE),
                ("phonetic", PHONETIC_WORK_QUEUE),
                ("spacy", SPACY_WORK_QUEUE),
            ]
            if not globals().get("VOICE_WORKER_ENABLED", False):
                specs.insert(1, ("voice", VOICE_WORK_QUEUE))
            for kind, queue_obj in specs:
                try:
                    queue_obj.warm(f"warm:{kind}", warm_language_worker, kind, timeout=min(45, queue_obj.timeout_seconds))
                    if "stt_debug_log" in globals():
                        stt_debug_log("process_worker_warmed", kind=kind, workers=queue_obj.max_workers)
                except Exception as exc:
                    if "stt_debug_log" in globals():
                        stt_debug_log("process_worker_warm_failed", kind=kind, error=str(exc))
            try:
                if globals().get("VOICE_WORKER_ENABLED", False) and callable(globals().get("ensure_voice_worker_process")):
                    # Added 2026-07-10: warm Kokoro/Edge VI chat voices inside the detached voice worker at startup.
                    ensure_voice_worker_process(preload=True, warm_model=True)
                    if "stt_debug_log" in globals():
                        stt_debug_log("voice_worker_warm_requested")
                    return
                time.sleep(18.0)
                VOICE_WORK_QUEUE.run(
                    "warm:voice-model",
                    warm_language_worker,
                    "voice-model",
                    timeout=min(120, VOICE_WORK_QUEUE.timeout_seconds),
                )
                if "stt_debug_log" in globals():
                    stt_debug_log("process_worker_voice_model_warmed")
            except Exception as exc:
                if "stt_debug_log" in globals():
                    stt_debug_log("process_worker_voice_model_warm_failed", error=str(exc))
        except Exception as exc:
            if "stt_debug_log" in globals():
                stt_debug_log("process_workers_warm_failed", error=str(exc))

    threading.Thread(target=worker, name="future-process-workers-warm", daemon=True).start()


def server_workload_snapshot() -> dict:
    guard = cpu_guard_settings_snapshot()
    return {
        "cpu_percent": round(current_system_cpu_percent(), 1),
        "cpu_queue_threshold": int(guard.get("threshold", WORKLOAD_CPU_HIGH_PERCENT) or WORKLOAD_CPU_HIGH_PERCENT),
        "cpu_guard_enabled": bool(guard.get("enabled", True)),
        "queues": {key: queue_obj.snapshot() for key, queue_obj in SERVER_WORK_QUEUES.items()},
    }
