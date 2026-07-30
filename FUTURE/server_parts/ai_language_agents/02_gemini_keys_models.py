# Loaded by FUTURE.server_parts.04_ai_language_agents into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def load_gemini_api_keys(force_refresh: bool = False) -> list[str]:
    """Load the local Gemini free-key queue without logging or exposing keys."""
    global GEMINI_KEY_CACHE
    try:
        stat = GEMINI_KEY_FILE.stat()
        mtime_ns = int(stat.st_mtime_ns)
    except Exception:
        mtime_ns = -1
    with GEMINI_KEY_LOCK:
        if not force_refresh and GEMINI_KEY_CACHE.get("mtime_ns") == mtime_ns:
            return list(GEMINI_KEY_CACHE.get("keys") or [])
        raw = ""
        if mtime_ns >= 0:
            for enc in ("utf-8-sig", "utf-8", "cp1252"):
                try:
                    raw = GEMINI_KEY_FILE.read_text(encoding=enc, errors="replace")
                    break
                except Exception:
                    raw = ""
        keys: list[str] = []
        seen: set[str] = set()
        for line in str(raw or "").splitlines():
            source = clean(line)
            if not source or source.startswith("#") or source.startswith("//") or source.startswith(";"):
                continue
            if "=" in source:
                left, right = source.split("=", 1)
                if clean(left).lower() in {"key", "api_key", "gemini_key", "gemini_api_key"}:
                    source = clean(right)
            for match in GEMINI_KEY_RE.findall(source):
                if match not in seen:
                    seen.add(match)
                    keys.append(match)
        GEMINI_KEY_CACHE = {"mtime_ns": mtime_ns, "keys": keys}
        return list(keys)


def ordered_gemini_api_keys() -> list[str]:
    global GEMINI_KEY_QUEUE_INDEX
    keys = load_gemini_api_keys()
    if not keys:
        return []
    with GEMINI_KEY_LOCK:
        start = GEMINI_KEY_QUEUE_INDEX % len(keys)
        GEMINI_KEY_QUEUE_INDEX = (GEMINI_KEY_QUEUE_INDEX + 1) % len(keys)
    return keys[start:] + keys[:start]


def extract_gemini_text(data: dict) -> str:
    if not isinstance(data, dict):
        return ""
    parts_out: list[str] = []
    candidates = data.get("candidates", []) if isinstance(data.get("candidates", []), list) else []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content", {}) if isinstance(candidate.get("content", {}), dict) else {}
        parts = content.get("parts", []) if isinstance(content.get("parts", []), list) else []
        for part in parts:
            if not isinstance(part, dict):
                continue
            text = str(part.get("text", "") or "").strip()
            if text:
                parts_out.append(text)
        if parts_out:
            break
    return "\n".join(parts_out).strip()


def gemini_error_message(data: dict, status: int = 0) -> str:
    if isinstance(data, dict):
        err = data.get("error", {})
        if isinstance(err, dict):
            msg = clean(err.get("message", ""))
            if msg:
                return msg
    return f"Gemini HTTP error {status}" if status else "Gemini did not return text."


def gemini_is_quota_problem(message: str) -> bool:
    low = clean(message).lower()
    return any(part in low for part in (
        "quota",
        "rate limit",
        "resource exhausted",
        "exceeded",
        "retry in",
        "429",
    ))


def gemini_is_key_problem(message: str) -> bool:
    low = clean(message).lower()
    return any(part in low for part in (
        "api key not valid",
        "permission denied",
        "unauthenticated",
        "invalid api key",
        "api_key_invalid",
        "403",
        "401",
    ))


def gemini_should_try_next_key(message: str) -> bool:
    low = clean(message).lower()
    return any(part in low for part in (
        "quota",
        "rate limit",
        "resource exhausted",
        "api key not valid",
        "permission denied",
        "unauthenticated",
        "invalid api key",
        "billing",
        "exceeded",
        "429",
        "403",
        "401",
    ))


def gemini_retry_delay_seconds(data: dict | None = None, message: str = "") -> float:
    if isinstance(data, dict):
        err = data.get("error", {})
        details = err.get("details", []) if isinstance(err, dict) and isinstance(err.get("details", []), list) else []
        for detail in details:
            if not isinstance(detail, dict):
                continue
            retry = clean(detail.get("retryDelay", ""))
            if retry:
                match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*s", retry.lower())
                if match:
                    try:
                        return max(1.0, float(match.group(1)))
                    except Exception:
                        pass
    match = re.search(r"retry\s+in\s+([0-9]+(?:\.[0-9]+)?)\s*s", clean(message).lower())
    if match:
        try:
            return max(1.0, float(match.group(1)))
        except Exception:
            pass
    return 0.0


def gemini_model_cooldown_key(api_key: str, model: str) -> str:
    return f"{gemini_key_cache_id(api_key)}:{clean(model).lower()}"


def gemini_model_is_on_cooldown(api_key: str, model: str) -> bool:
    key = gemini_model_cooldown_key(api_key, model)
    until = float(GEMINI_MODEL_COOLDOWN.get(key) or 0)
    if until <= time.time():
        GEMINI_MODEL_COOLDOWN.pop(key, None)
        return False
    return True


def gemini_mark_model_cooldown(api_key: str, model: str, seconds: float) -> None:
    if seconds <= 0:
        seconds = 60.0
    key = gemini_model_cooldown_key(api_key, model)
    GEMINI_MODEL_COOLDOWN[key] = max(float(GEMINI_MODEL_COOLDOWN.get(key) or 0), time.time() + min(max(seconds, 5.0), 900.0))


def gemini_is_model_problem(message: str) -> bool:
    low = clean(message).lower()
    return any(part in low for part in (
        "model not found",
        "models/",
        "not found for api version",
        "not supported for generatecontent",
        "not supported for generate content",
        "generatecontent is not supported",
        "unsupported model",
    ))


def gemini_text_model_sort_key(model: str) -> tuple[int, str]:
    low = clean(model).lower()
    if "lite" in low and "3.1" in low and "flash" in low:
        return (0, low)
    if "lite" in low and "2.5" in low and "flash" in low:
        return (1, low)
    if "lite" in low and "2.0" in low and "flash" in low:
        return (2, low)
    if "flash" in low and "3.5" in low:
        return (3, low)
    if "flash" in low and "2.5" in low:
        return (4, low)
    if "flash" in low and "2.0" in low:
        return (5, low)
    if "flash" in low and "1.5" in low:
        return (6, low)
    if "pro" in low:
        return (30, low)
    return (20, low)


def gemini_text_model_allowed(model: str) -> bool:
    low = clean(model).lower()
    if not low:
        return False
    if "generate" in low and "content" in low:
        return False
    return not any(blocked in low for blocked in (
        "embedding",
        "imagen",
        "image",
        "tts",
        "audio",
        "video",
        "veo",
        "lyria",
        "live",
        "aqa",
    ))


def gemini_text_model_candidates(api_key: str = "") -> list[str]:
    models = [model for model in GEMINI_TEXT_MODELS if gemini_text_model_allowed(model)]
    if api_key:
        models.extend(model for model in list_gemini_generate_models(api_key) if gemini_text_model_allowed(model))
    deduped: list[str] = []
    seen: set[str] = set()
    for model in sorted(models, key=gemini_text_model_sort_key):
        if model not in seen:
            deduped.append(model)
            seen.add(model)
    return deduped


def gemini_key_cache_id(api_key: str) -> str:
    return hashlib.sha256(str(api_key or "").encode("utf-8", errors="ignore")).hexdigest()[:16]


def gemini_api_headers(api_key: str, content_type: str = "") -> dict:
    headers = {"Accept": "application/json", "x-goog-api-key": clean(api_key)}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def list_gemini_generate_models(api_key: str) -> list[str]:
    cache_id = gemini_key_cache_id(api_key)
    now = time.time()
    cached = GEMINI_MODEL_CACHE.get(cache_id)
    if cached and now - cached[0] < GEMINI_MODEL_CACHE_SECONDS:
        return list(cached[1])
    models: list[str] = []
    try:
        def fetch_models() -> bytes:
            from future_ipv4_http import ipv4_https_request_bytes

            raw, _timing = ipv4_https_request_bytes(
                GEMINI_API_BASE,
                headers=gemini_api_headers(api_key),
                method="GET",
                timeout=12.0,
            )
            return raw

        raw = fetch_models()
        data = json.loads(raw.decode("utf-8", errors="replace") or "{}")
        entries = data.get("models", []) if isinstance(data.get("models", []), list) else []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            methods = entry.get("supportedGenerationMethods", [])
            methods_text = " ".join(str(item).lower() for item in methods if item is not None)
            if "generatecontent" not in methods_text:
                continue
            name = clean(entry.get("name", ""))
            if not name:
                continue
            short_name = name.split("/", 1)[1] if name.startswith("models/") else name
            short_low = short_name.lower()
            if any(blocked in short_low for blocked in ("embedding", "aqa", "imagen", "image", "tts", "audio", "video", "veo", "lyria", "live")):
                continue
            models.append(short_name)
    except Exception:
        models = []

    deduped: list[str] = []
    seen: set[str] = set()
    for model in sorted(models, key=gemini_text_model_sort_key):
        if model not in seen:
            deduped.append(model)
            seen.add(model)
    GEMINI_MODEL_CACHE[cache_id] = (now, deduped)
    return list(deduped)


def request_gemini_model_once(api_key: str, model: str, body: bytes) -> dict:
    request_id = f"gemini-{uuid.uuid4().hex[:12]}"
    # Updated 2026-07-22: keep Gemini local IPv4 by default while the packaged worker is being repaired.
    use_worker = clean(os.environ.get("FUTURE_GEMINI_USE_DISTRIBUTED_WORKER", "")).lower() in {"1", "true", "yes", "on"}
    worker_gemini = globals().get("distributed_worker_try_gemini_model_once")
    worker_available = globals().get("distributed_worker_gemini_available")
    if use_worker and callable(worker_gemini) and callable(worker_available) and worker_available():
        worker_started = time.perf_counter()
        try:
            remote = worker_gemini(model, body, timeout_seconds=20.0)
            if isinstance(remote, dict) and remote:
                remote.setdefault("_future_gemini", {})
                remote["_future_gemini"].update({"request_id": request_id, "attempt_id": "worker-1", "worker_wait_ms": round((time.perf_counter() - worker_started) * 1000.0, 3)})
                return remote
        except Exception as exc:
            raise RuntimeError(f"Gemini worker attempt failed ({request_id}): {exc}") from exc
        raise TimeoutError(f"Gemini worker attempt timed out ({request_id}); duplicate local retry suppressed.")

    def fetch_content() -> bytes:
        from future_ipv4_http import ipv4_https_request_bytes

        url = f"{GEMINI_API_BASE}/{model}:generateContent"
        raw, timing = ipv4_https_request_bytes(
            url,
            data=body,
            headers=gemini_api_headers(api_key, "application/json; charset=utf-8"),
            method="POST",
            timeout=20.0,
        )
        fetch_content.timing = timing
        return raw

    raw = fetch_content()
    data = json.loads(raw.decode("utf-8", errors="replace") or "{}")
    if isinstance(data, dict):
        data["_future_gemini"] = {**getattr(fetch_content, "timing", {}), "request_id": request_id, "attempt_id": "local-ipv4-1"}
    return data
