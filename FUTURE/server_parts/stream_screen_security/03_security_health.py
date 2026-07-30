# Loaded by FUTURE.server_parts.05_stream_screen_security into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def is_local_client(address: str) -> bool:
    host = clean(address)
    return host in ("127.0.0.1", "::1", "localhost") or host.startswith("127.")


def is_private_or_local_host(host: str) -> bool:
    raw = clean(host).strip("[]").lower()
    if not raw:
        return False
    if raw == "localhost" or raw.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(raw)
        return ip.is_loopback or ip.is_private or ip.is_link_local
    except ValueError:
        return False


def origin_of_url(value: str) -> str:
    parsed = urlparse(clean(value))
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def hostname_from_host_header(host_header: str) -> str:
    raw = clean(host_header)
    if not raw:
        return ""
    parsed = urlparse(f"//{raw}")
    if parsed.hostname:
        return parsed.hostname
    return raw.rsplit(":", 1)[0]


def request_host_is_private_or_local(host_header: str) -> bool:
    return is_private_or_local_host(hostname_from_host_header(host_header))


def should_serve_obfuscated_frontend(client_address: str, host_header: str) -> bool:
    return not (is_local_client(client_address) and request_host_is_private_or_local(host_header))


# Added 2026-07-09: exposes recent rate-limit/security alerts to the local dashboard only.
def security_rate_alerts_snapshot(limit: int = 20) -> list[dict]:
    now = time.time()
    with SECURITY_ALERT_LOCK:
        stale = [
            key for key, item in SECURITY_RATE_ALERTS.items()
            if now - float((item or {}).get("last_at", now) or now) > 3600
        ]
        for key in stale:
            SECURITY_RATE_ALERTS.pop(key, None)
        rows = [dict(item) for item in SECURITY_RATE_ALERTS.values() if isinstance(item, dict)]
    rows.sort(key=lambda item: float(item.get("last_at", 0) or 0), reverse=True)
    return rows[: max(1, min(80, int(limit or 20)))]


# Added 2026-07-09: summarizes top pollers and lightweight server-process CPU while poll traffic is active.
def security_poll_dashboard_snapshot(limit: int = 12) -> dict:
    now = time.time()
    with SECURITY_ALERT_LOCK:
        stale = [
            key for key, item in SECURITY_POLL_STATS.items()
            if now - float((item or {}).get("last_at", now) or now) > 180
        ]
        for key in stale:
            SECURITY_POLL_STATS.pop(key, None)
        rows = [dict(item) for item in SECURITY_POLL_STATS.values() if isinstance(item, dict)]
        blocks = [dict(item) for item in SECURITY_BLOCKS.values() if isinstance(item, dict) and float(item.get("until", 0) or 0) > now]
        poll_cpu = round(float(SECURITY_POLL_CPU_SAMPLE.get("percent", 0.0) or 0.0), 1)
    rows.sort(key=lambda item: (int(item.get("count", 0) or 0), float(item.get("last_at", 0) or 0)), reverse=True)
    total = sum(int(item.get("count", 0) or 0) for item in rows)
    return {
        "poll_cpu_percent": poll_cpu,
        "poll_cpu_alert": bool(poll_cpu >= 20 and total > 0),
        "total_recent": total,
        "top": rows[: max(1, min(40, int(limit or 12)))],
        "blocked": blocks,
    }


# Added 2026-07-09: local dashboard action to temporarily block a noisy user or IP.
def security_block_poll_identity(identity_type: str, identity: str, minutes: int = 10) -> dict:
    kind = clean(identity_type).lower()
    if kind not in {"user", "ip"}:
        raise RuntimeError("Loai block khong hop le.")
    value = normalize_username(identity) if kind == "user" else clean(identity)
    if not value:
        raise RuntimeError("Thieu user/IP de chan.")
    minutes = max(1, min(1440, int(minutes or 10)))
    now = time.time()
    key = f"{kind}:{value}"
    with SECURITY_ALERT_LOCK:
        SECURITY_BLOCKS[key] = {
            "type": kind,
            "identity": value,
            "key": key,
            "blocked_at": utc_timestamp(),
            "until": now + minutes * 60,
            "minutes": minutes,
        }
    return {"blocked": True, "type": kind, "identity": value, "minutes": minutes}


def allowed_cors_origin(origin: str, client_address: str = "") -> str:
    raw = clean(origin)
    if not raw:
        return ""
    if raw == "null":
        return "null" if is_local_client(client_address) else ""
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return ""
    if is_private_or_local_host(parsed.hostname):
        return raw
    normalized = origin_of_url(raw)
    allowed = set()
    for key in ("public_url", "public_app_url"):
        item = origin_of_url(clean(SERVER_STATE.get(key, "")))
        if item:
            allowed.add(item)
    for item in SERVER_STATE.get("server_urls", []) or []:
        origin_item = origin_of_url(clean(item))
        if origin_item:
            allowed.add(origin_item)
    return raw if normalized and normalized in allowed else ""


PUBLIC_HEALTH_STT_PROBE_LOCK = threading.Lock()
PUBLIC_HEALTH_STT_PROBE_AT = 0.0
PUBLIC_HEALTH_STT_PROBE_RESULT = None
PUBLIC_HEALTH_STT_PROBE_MAX_AGE_SECONDS = 2.0
PUBLIC_HEALTH_RESPONSE_CACHE_LOCK = threading.Lock()
PUBLIC_HEALTH_RESPONSE_CACHE: dict[tuple[bool, bool], dict] = {}
PUBLIC_HEALTH_RESPONSE_CACHE_SECONDS = 0.25


# Added 2026-07-20: coalesce concurrent dashboard probes instead of serially polling the STT worker per request.
def refresh_public_health_stt_worker() -> dict | None:
    global PUBLIC_HEALTH_STT_PROBE_AT, PUBLIC_HEALTH_STT_PROBE_RESULT
    now = time.monotonic()
    if now - PUBLIC_HEALTH_STT_PROBE_AT <= PUBLIC_HEALTH_STT_PROBE_MAX_AGE_SECONDS:
        return PUBLIC_HEALTH_STT_PROBE_RESULT
    with PUBLIC_HEALTH_STT_PROBE_LOCK:
        now = time.monotonic()
        if now - PUBLIC_HEALTH_STT_PROBE_AT <= PUBLIC_HEALTH_STT_PROBE_MAX_AGE_SECONDS:
            return PUBLIC_HEALTH_STT_PROBE_RESULT
        try:
            PUBLIC_HEALTH_STT_PROBE_RESULT = stt_worker_health(timeout=1.5)
        except Exception:
            PUBLIC_HEALTH_STT_PROBE_RESULT = None
        PUBLIC_HEALTH_STT_PROBE_AT = time.monotonic()
        return PUBLIC_HEALTH_STT_PROBE_RESULT


def public_health_payload(local_client: bool = False) -> dict:
    refresh_public_health_stt_worker()
    payload = {key: SERVER_STATE.get(key) for key in sorted(PUBLIC_SERVER_STATE_KEYS)}
    payload["server_time"] = chat_now()
    payload["server_timestamp"] = utc_timestamp()
    payload["workload"] = server_workload_snapshot()
    try:
        payload["distributed_workers"] = distributed_worker_dashboard_payload(local_client)
    except Exception as exc:
        payload["distributed_workers"] = {"enabled": False, "error": str(exc), "workers": []}
    if local_client:
        payload.update({key: SERVER_STATE.get(key) for key in sorted(LOCAL_SERVER_STATE_KEYS)})
        payload["postgres_writer"] = server_database_write_metrics_snapshot()
        postgres_metrics = globals().get("postgres_metrics_snapshot")
        if callable(postgres_metrics):
            payload["postgres"] = postgres_metrics()
        postgres_probe = globals().get("postgres_runtime_probe_snapshot")
        if callable(postgres_probe) and os.environ.get("FUTURE_READINESS_PROBE") == "1":
            payload["postgres_probe"] = postgres_probe()
            payload["server_data_root"] = str(SERVER_DATA_ROOT)
            payload["qmlearn_root"] = str(QMLEARN_ROOT)
        leaderboard_metrics = globals().get("leaderboard_runtime_metrics_snapshot")
        if callable(leaderboard_metrics):
            payload["leaderboard_runtime"] = leaderboard_metrics()
        rollout_snapshot = globals().get("canonical_identity_rollout_snapshot")
        if callable(rollout_snapshot):
            payload["canonical_identity_rollout"] = rollout_snapshot()
        payload["security_alerts"] = security_rate_alerts_snapshot(20)
        payload["security_poll"] = security_poll_dashboard_snapshot(12)
    return payload


# Added 2026-07-20: reuse final JSON bytes for concurrent global health reads with a bounded freshness window.
def public_health_response_bytes(local_client: bool = False, include_settings: bool = True) -> tuple[bytes, bool]:
    key = (bool(local_client), bool(include_settings))
    now = time.monotonic()
    with PUBLIC_HEALTH_RESPONSE_CACHE_LOCK:
        cached = PUBLIC_HEALTH_RESPONSE_CACHE.get(key)
        if cached and now - float(cached.get("built_at", 0) or 0) <= PUBLIC_HEALTH_RESPONSE_CACHE_SECONDS:
            return bytes(cached.get("data") or b""), True
        payload = {"ok": True, "service": "future-whisper", **public_health_payload(local_client)}
        if include_settings:
            payload["settings"] = public_server_settings()
        data = json_bytes(payload)
        PUBLIC_HEALTH_RESPONSE_CACHE[key] = {"built_at": time.monotonic(), "data": data}
        return data, False
