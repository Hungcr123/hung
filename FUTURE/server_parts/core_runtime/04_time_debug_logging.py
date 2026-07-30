# Loaded by FUTURE.server_parts.01_core_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def local_timestamp(epoch: float | None = None) -> str:
    value = time.time() if epoch is None else float(epoch or time.time())
    # Keep local wall-clock dates for dashboards while making the instant
    # unambiguous to clients in other timezones.
    return datetime.fromtimestamp(value).astimezone().isoformat(timespec="seconds")


def utc_timestamp() -> str:
    # The dashboard presents server timestamps as local machine time.
    return local_timestamp()


def timestamp_to_epoch(value: object) -> float:
    raw = clean(value)
    if not raw:
        return 0.0
    try:
        iso_value = raw[:-1] + "+00:00" if raw.upper().endswith("Z") else raw
        return datetime.fromisoformat(iso_value).timestamp()
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt).timestamp()
        except Exception:
            continue
    return 0.0


def timestamp_order_key(value: object) -> tuple[int, float, str]:
    raw = clean(value)
    epoch = timestamp_to_epoch(raw)
    # Parseable timestamps always outrank legacy/unparseable text; raw text is only a stable fallback.
    return (1 if epoch > 0 else 0, epoch, raw)


def timestamp_latest_text(*values: object) -> str:
    candidates = [clean(value) for value in values if clean(value)]
    return max(candidates, key=timestamp_order_key) if candidates else ""


def timestamp_earliest_text(*values: object) -> str:
    candidates = [clean(value) for value in values if clean(value)]
    if not candidates:
        return ""
    parseable = [value for value in candidates if timestamp_to_epoch(value) > 0]
    return min(parseable or candidates, key=timestamp_order_key)


def timestamp_same_instant(left: object, right: object) -> bool:
    left_raw = clean(left)
    right_raw = clean(right)
    left_epoch = timestamp_to_epoch(left_raw)
    right_epoch = timestamp_to_epoch(right_raw)
    if left_epoch > 0 and right_epoch > 0:
        return abs(left_epoch - right_epoch) < 0.001
    return left_raw == right_raw


_LOCAL_OFFSET_RAW = datetime.now().astimezone().strftime("%z")
SERVER_LOCAL_TIMEZONE_SUFFIX = f"{_LOCAL_OFFSET_RAW[:3]}:{_LOCAL_OFFSET_RAW[3:]}" if len(_LOCAL_OFFSET_RAW) == 5 else "+00:00"


def normalize_timestamp_text(value: object = "", fallback_now: bool = False) -> str:
    raw = clean(value)
    if not raw:
        return utc_timestamp() if fallback_now else ""
    if raw.upper().endswith("Z") or re.search(r"[+-]\d{2}:?\d{2}$", raw):
        return raw
    legacy = re.fullmatch(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2}(?:\.\d+)?)", raw)
    if legacy:
        return f"{legacy.group(1)}T{legacy.group(2)}{SERVER_LOCAL_TIMEZONE_SUFFIX}"
    epoch = timestamp_to_epoch(raw)
    return local_timestamp(epoch) if epoch > 0 else (utc_timestamp() if fallback_now else raw)


def month_ago_epoch() -> float:
    return time.time() - 31 * 24 * 60 * 60

STT_DEBUG_LOG_MAX_BYTES = 500 * 1024
STT_DEBUG_LOG_KEEP_BYTES = 250 * 1024


def trim_stt_debug_log_locked() -> None:
    # Keep the debug log bounded. Once it grows past STT_DEBUG_LOG_MAX_BYTES we
    # drop the oldest content and keep only the most recent tail, so recent
    # diagnostics survive while the file can never grow without limit. Caller
    # must already hold STT_DEBUG_LOCK.
    try:
        if not STT_DEBUG_LOG_FILE.is_file():
            return
        size = STT_DEBUG_LOG_FILE.stat().st_size
        if size <= STT_DEBUG_LOG_MAX_BYTES:
            return
        keep = max(0, min(int(STT_DEBUG_LOG_KEEP_BYTES), int(STT_DEBUG_LOG_MAX_BYTES)))
        with STT_DEBUG_LOG_FILE.open("rb") as fh:
            if keep > 0:
                fh.seek(-keep, os.SEEK_END)
                tail = fh.read()
            else:
                tail = b""
        # Start at the first full line so we never keep a half-truncated record.
        newline = tail.find(b"\n")
        if newline != -1:
            tail = tail[newline + 1:]
        with STT_DEBUG_LOG_FILE.open("wb") as fh:
            fh.write(tail)
    except Exception:
        pass



def stt_debug_log(event: str, **fields) -> None:
    try:
        SERVER_LOG_ROOT.mkdir(parents=True, exist_ok=True)
        payload = {
            "at": utc_timestamp(),
            "pid": os.getpid(),
            "event": clean(event),
        }
        for key, value in fields.items():
            try:
                if isinstance(value, (str, int, float, bool)) or value is None:
                    payload[str(key)] = value
                else:
                    payload[str(key)] = str(value)
            except Exception:
                payload[str(key)] = "<unserializable>"
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with STT_DEBUG_LOCK:
            trim_stt_debug_log_locked()
            with STT_DEBUG_LOG_FILE.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except Exception:
        pass


def enable_stt_fault_logging() -> None:
    global STT_FAULT_LOG_HANDLE
    try:
        SERVER_LOG_ROOT.mkdir(parents=True, exist_ok=True)
        if STT_FAULT_LOG_HANDLE is None or STT_FAULT_LOG_HANDLE.closed:
            STT_FAULT_LOG_HANDLE = STT_FAULT_LOG_FILE.open("a", encoding="utf-8")
        faulthandler.enable(file=STT_FAULT_LOG_HANDLE, all_threads=True)
        stt_debug_log("fault_handler_enabled", file=str(STT_FAULT_LOG_FILE))
    except Exception as exc:
        stt_debug_log("fault_handler_enable_failed", error=str(exc))
