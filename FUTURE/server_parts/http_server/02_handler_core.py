# Loaded by FUTURE.server_parts.11_http_server into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def end_headers(self):
    origin = clean(self.headers.get("Origin", ""))
    client_address = ""
    try:
        client_address = clean(self.client_address[0])
    except Exception:
        client_address = ""
    cors_origin = allowed_cors_origin(origin, client_address)
    if cors_origin:
        self.send_header("Access-Control-Allow-Origin", cors_origin)
        self.send_header("Vary", "Origin")
    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, If-None-Match, X-Future-Auth, X-Future-Anti-Robot, X-Future-Email-Secret, X-Future-Completion-Trace, Access-Control-Request-Private-Network")
    self.send_header("Access-Control-Expose-Headers", "Content-Length, Content-Type, Content-Range, ETag, X-Future-Cache-Hit, X-Future-Disk-Cache-Hit, X-Future-Render-Ms, X-Future-Payload-Bytes, X-Future-Encoder, X-Future-File-Bytes, X-Future-File-Mtime, X-Future-File-Path, Server-Timing")
    self.send_header("Access-Control-Allow-Private-Network", "true")
    self.send_header("Access-Control-Max-Age", "86400")
    self.send_header("X-Content-Type-Options", "nosniff")
    self.send_header("Referrer-Policy", "no-referrer")
    self.send_header("X-Frame-Options", "SAMEORIGIN")
    BaseHTTPRequestHandler.end_headers(self)


# Added 2026-07-29: request-level completion trace for one real runtime replay.
def completion_trace_begin(self, path: str, trace_id_override: str = "") -> None:
    trace_id = clean(trace_id_override or self.headers.get("X-Future-Completion-Trace", ""))[:160]
    if not trace_id:
        return
    traced = {
        "/space-v/progress", "/lesson/complete", "/vocab/registry/sync",
        "/vocab/registry", "/vocab/leaderboard", "/space-w/progress",
        "/lesson-tasks/status",
    }
    if path not in traced:
        return
    pg_trace_begin = globals().get("postgres_trace_begin")
    if callable(pg_trace_begin):
        pg_trace_begin(trace_id)
    pg = globals().get("postgres_metrics_snapshot")
    self._future_completion_trace = {
        "trace_id": trace_id,
        "route": path,
        "client_source": clean((parse_qs(urlparse(self.path).query).get("client_source") or [""])[0]),
        "started_wall": time.perf_counter_ns(),
        "started_thread_cpu": time.thread_time_ns(),
        "started_process_cpu": time.process_time_ns(),
        "postgres_before": pg() if callable(pg) else {},
    }


def completion_trace_finish(self, status: int, response_bytes: int) -> None:
    trace = getattr(self, "_future_completion_trace", None)
    if not isinstance(trace, dict):
        return
    pg = globals().get("postgres_metrics_snapshot")
    after = pg() if callable(pg) else {}
    before = trace.get("postgres_before") if isinstance(trace.get("postgres_before"), dict) else {}
    delta = {key: int(after.get(key, 0) or 0) - int(before.get(key, 0) or 0) for key in ("transactions", "commits", "rollbacks", "sql_round_trips")}
    pg_trace_finish = globals().get("postgres_trace_finish")
    isolated_postgres = pg_trace_finish() if callable(pg_trace_finish) else {}
    if clean(os.environ.get("FUTURE_COMPLETION_TRACE_DISK_LOG", "")).lower() in {"1", "true", "yes", "on"}:
        stt_debug_log(
            "completion_trace_request",
            trace_id=trace.get("trace_id", ""), route=trace.get("route", ""),
            client_source=trace.get("client_source", ""), status=int(status),
            wall_ms=round((time.perf_counter_ns() - int(trace.get("started_wall", 0) or 0)) / 1e6, 3),
            thread_cpu_ms=round((time.thread_time_ns() - int(trace.get("started_thread_cpu", 0) or 0)) / 1e6, 3),
            process_cpu_delta_ms=round((time.process_time_ns() - int(trace.get("started_process_cpu", 0) or 0)) / 1e6, 3),
            postgres=delta, isolated_postgres=isolated_postgres, response_bytes=int(response_bytes or 0),
        )
    self._future_completion_trace = None

def send_json(self, status: int, payload: dict, extra_headers: dict | None = None, timing_label: str = ""):
    payload = dict(payload or {})
    trace = getattr(self, "_future_completion_trace", None)
    if isinstance(trace, dict) and trace.get("route") == "/lesson/complete":
        pg_trace_stage = globals().get("postgres_trace_set_stage")
        if callable(pg_trace_stage):
            pg_trace_stage("response_serialization")
    if status == 401 and payload.get("ok") is False and "reason" not in payload:
        reason = clean(getattr(self, "_auth_error_reason", ""))
        if reason:
            payload["reason"] = reason
    data = json_bytes(payload)
    self._future_last_response_status = int(status)
    self._future_last_response_bytes = len(data)
    self.send_response(status)
    if status >= 400:
        self.close_connection = True
        self.send_header("Connection", "close")
    if isinstance(extra_headers, dict):
        for key, value in extra_headers.items():
            if clean(key) and clean(value):
                self.send_header(clean(key), clean(value))
    self.send_header("Content-Type", "application/json; charset=utf-8")
    self.send_header("Content-Length", str(len(data)))
    queue_wait_ms = self.request_queue_wait_ms()
    write_started = time.perf_counter()
    ok = self.safe_finish_response(data)
    self.completion_trace_finish(status, len(data))
    if clean(timing_label):
        stt_debug_log(
            clean(timing_label),
            status=status,
            bytes=len(data),
            ok=bool(ok),
            queue_wait_ms=round(queue_wait_ms, 3),
            handler_elapsed_ms=round(self.request_handler_elapsed_ms(), 3),
            write_ms=round((time.perf_counter() - write_started) * 1000, 3),
        )
    return ok

def safe_finish_response(self, data: bytes = b"") -> bool:
    try:
        if not data:
            self.close_connection = True
            self.send_header("Connection", "close")
        self.end_headers()
        if data:
            self.wfile.write(data)
        return True
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        return False
    except OSError as exc:
        if getattr(exc, "winerror", None) in {10053, 10054, 10058}:
            return False
        raise

def anti_robot_client_key(self) -> str:
    return anti_robot_client_ip(self.headers, self.client_address)

# Added 2026-07-28: measures process_request-to-handler-entry time for queue diagnostics.
def request_queue_wait_ms(self) -> float:
    if not bool(getattr(self, "_future_handler_is_first_request", True)):
        return 0.0
    server = getattr(self, "server", None)
    request = getattr(self, "request", None)
    if server is None or request is None:
        return 0.0
    getter = getattr(server, "_future_request_accept_times", None)
    lock = getattr(server, "_future_request_accept_times_lock", None)
    try:
        fileno = int(request.fileno())
    except Exception:
        return 0.0
    if fileno < 0 or not isinstance(getter, dict):
        return 0.0
    accepted_at = None
    if hasattr(lock, "__enter__"):
        with lock:
            accepted_at = getter.get(fileno)
    else:
        accepted_at = getter.get(fileno)
    if not accepted_at:
        return 0.0
    handler_started_at = float(getattr(self, "_future_handler_started_at", 0.0) or 0.0)
    if handler_started_at <= 0:
        return 0.0
    return max(0.0, (handler_started_at - float(accepted_at)) * 1000.0)

def request_handler_elapsed_ms(self) -> float:
    handler_started_at = float(getattr(self, "_future_handler_started_at", 0.0) or 0.0)
    if handler_started_at <= 0:
        return 0.0
    return max(0.0, (time.perf_counter() - handler_started_at) * 1000.0)

# Added 2026-07-09: reads the current auth username without touching session last_seen/disk.
def auth_username_light(self) -> str:
    token = clean(self.headers.get("Authorization", "")) or clean(self.headers.get("X-Future-Auth", ""))
    if not token:
        token = request_cookie_value(self.headers.get("Cookie", ""), AUTH_COOKIE_NAME)
    raw = clean(token)
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    if not raw:
        return ""
    with AUTH_LOCK:
        session = AUTH_SESSIONS.get(raw)
        if not isinstance(session, dict):
            return ""
        return normalize_username(session.get("username", ""))

def auth_admin_light(self) -> bool:
    try:
        username = self.auth_username_light()
        return bool(username and is_admin_user(username))
    except Exception:
        return False


# Added 2026-07-09: identifies lightweight poll/state routes for RAM-only anti-spam telemetry.
def security_poll_path(self, path: str) -> bool:
    target = clean(path)
    if self.anti_robot_realtime_path(target):
        return True
    return target in {
        "/frontend-version",
        "/auth/me",
        "/chat/poll",
        "/chat/admin/state",
        "/stream/state",
        "/stream/poll",
        "/stream/admin/poll",
        "/screen/state",
        "/paint/state",
        "/paint/admin/state",
        "/world/state",
        "/world/battle/state",
        "/world/training/state",
        "/game/state",
        "/space-w/speak-skip/state",
        "/vocab/sync-main-offline",
    }


# Added 2026-07-09: tracks poll pressure by user/ip/path without disk writes.
def record_security_poll_stat(self, path: str, method: str) -> None:
    if self.is_local_admin_request() or self.auth_admin_light() or not self.security_poll_path(path):
        return
    now = time.time()
    target = clean(path)[:160]
    verb = clean(method).upper()
    try:
        ip = clean(self.client_address[0] if self.client_address else "")
    except Exception:
        ip = ""
    username = self.auth_username_light()
    identity_type = "user" if username else "ip"
    identity = username or ip or self.anti_robot_client_key()
    key = f"{identity_type}:{identity}|{verb}|{target}"
    with SECURITY_ALERT_LOCK:
        sample_at = float(SECURITY_POLL_CPU_SAMPLE.get("at", now) or now)
        if now - sample_at >= 1.0:
            prev_cpu = float(SECURITY_POLL_CPU_SAMPLE.get("cpu", time.process_time()) or 0.0)
            current_cpu = time.process_time()
            elapsed = max(0.001, now - sample_at)
            SECURITY_POLL_CPU_SAMPLE.update({"at": now, "cpu": current_cpu, "percent": max(0.0, min(100.0, ((current_cpu - prev_cpu) / elapsed) * 100.0))})
        item = SECURITY_POLL_STATS.get(key) if isinstance(SECURITY_POLL_STATS.get(key), dict) else {}
        window_start = float(item.get("window_start", now) or now)
        if now - window_start >= 60:
            item = {"count": 0, "window_start": now, "first_at": now}
        item.update({
            "identity_type": identity_type,
            "identity": identity,
            "username": username,
            "ip": ip,
            "method": verb,
            "path": target,
            "count": int(item.get("count", 0) or 0) + 1,
            "last_at": now,
            "last_seen": utc_timestamp(),
            "user_agent": clean(self.headers.get("User-Agent", ""))[:180],
        })
        SECURITY_POLL_STATS[key] = item
        stale = [row_key for row_key, row in SECURITY_POLL_STATS.items() if now - float((row or {}).get("last_at", now) or now) > 180]
        for row_key in stale[:80]:
            SECURITY_POLL_STATS.pop(row_key, None)
        if len(SECURITY_POLL_STATS) > 120:
            ordered = sorted(SECURITY_POLL_STATS.items(), key=lambda row: float((row[1] or {}).get("last_at", 0) or 0))
            for old_key, _old in ordered[: max(1, len(SECURITY_POLL_STATS) - 120)]:
                SECURITY_POLL_STATS.pop(old_key, None)


# Added 2026-07-09: blocks dashboard-selected abusive poll clients/users from all non-local requests.
def enforce_security_block(self, path: str) -> bool:
    if self.is_local_admin_request():
        return True
    now = time.time()
    try:
        ip = clean(self.client_address[0] if self.client_address else "")
    except Exception:
        ip = ""
    username = self.auth_username_light()
    keys = [f"ip:{ip}"]
    if username:
        keys.append(f"user:{username}")
    with SECURITY_ALERT_LOCK:
        for key in list(SECURITY_BLOCKS.keys()):
            item = SECURITY_BLOCKS.get(key)
            if not isinstance(item, dict) or float(item.get("until", 0) or 0) <= now:
                SECURITY_BLOCKS.pop(key, None)
        for key in keys:
            item = SECURITY_BLOCKS.get(key)
            if isinstance(item, dict):
                retry_after = max(1, int(float(item.get("until", now) or now) - now))
                self.record_security_rate_alert(path, f"blocked_{key.split(':', 1)[0]}", retry_after)
                self.send_json(429, {
                    "ok": False,
                    "error": "May nay dang bi tam chan do poll qua nhieu. Hay thu lai sau.",
                    "reason": "security_blocked",
                    "retry_after": retry_after,
                })
                return False
    return True

# Added 2026-07-09: records blocked spam/rate-limit clients for the local server dashboard.
def record_security_rate_alert(self, path: str, reason: str, retry_after: int = 0) -> None:
    now = time.time()
    try:
        ip = clean(self.client_address[0] if self.client_address else "")
    except Exception:
        ip = ""
    user_agent = clean(self.headers.get("User-Agent", ""))[:180]
    host = clean(self.headers.get("Host", ""))[:120]
    target = clean(path)[:160]
    code = clean(reason)[:80] or "rate_limited"
    key = f"{ip}|{target}|{code}"
    with SECURITY_ALERT_LOCK:
        item = SECURITY_RATE_ALERTS.get(key) if isinstance(SECURITY_RATE_ALERTS.get(key), dict) else {}
        count = int(item.get("count", 0) or 0) + 1
        first_at = float(item.get("first_at", now) or now)
        SECURITY_RATE_ALERTS[key] = {
            "ip": ip,
            "host": host,
            "path": target,
            "reason": code,
            "count": count,
            "first_at": first_at,
            "last_at": now,
            "last_seen": utc_timestamp(),
            "retry_after": int(retry_after or 0),
            "user_agent": user_agent,
        }
        if len(SECURITY_RATE_ALERTS) > 80:
            ordered = sorted(SECURITY_RATE_ALERTS.items(), key=lambda row: float((row[1] or {}).get("last_at", 0) or 0))
            for old_key, _old in ordered[: max(1, len(SECURITY_RATE_ALERTS) - 80)]:
                SECURITY_RATE_ALERTS.pop(old_key, None)

def anti_robot_realtime_path(self, path: str) -> bool:
    target = clean(path)
    return target in {
        "/paint/state",
        "/paint/admin/state",
        "/paint/sync",
        "/paint/cursor",
        "/paint/admin/sync",
        "/paint/admin/cursor",
        "/screen/frame",
        "/screen/frame-binary",
        "/screen/audio-chunk",
        "/screen/auth-admin/audio-chunk",
        "/screen/audio",
        "/screen/control",
        "/screen/admin/audio",
        "/screen/auth-admin/audio",
        "/screen/auth-admin/frame",
        "/screen/auth-admin/control",
        "/screen/admin/frame",
        "/screen/admin/control",
    }

def enforce_anti_robot_rate(self, path: str, method: str) -> bool:
    if auth_limits_disabled_for_benchmark():
        return True
    target = clean(path)
    verb = clean(method).upper()
    if self.is_local_admin_request() or self.auth_admin_light():
        return True
    if self.anti_robot_realtime_path(target):
        client_key = self.anti_robot_client_key()
        limit = ANTI_ROBOT_WORLD_GET_LIMIT if verb == "GET" else ANTI_ROBOT_WORLD_POST_LIMIT
        ok, retry_after = anti_robot_rate_allowed(f"REALTIME:{verb}:{target}:{client_key}", limit, 60)
        if not ok:
            self.record_security_rate_alert(target, "realtime_rate_limited", retry_after)
            self.send_json(429, {
                "ok": False,
                "error": "Realtime poll qua nhanh. Vui long thu lai sau vai giay.",
                "retry_after": retry_after,
                "reason": "realtime_rate_limited",
            })
            return False
        return True
    client_key = self.anti_robot_client_key()
    limit = ANTI_ROBOT_GET_LIMIT if verb == "GET" else ANTI_ROBOT_POST_LIMIT
    window_seconds = 60
    if target in {"/auth/login", "/auth/register"}:
        limit = ANTI_ROBOT_AUTH_LIMIT
    elif target in {
        "/ai-agent/ask",
        "/ai-agent/space-p/followup",
        "/ai-agent/translate",
        "/word-agent/ask",
        "/pdf/translate",
        "/pdf/speak-training/reference",
    }:
        limit = ANTI_ROBOT_AI_LIMIT
    elif target in {
        "/pdf/ocr",
        "/picture/ocr",
        "/pdf/scan-page",
        "/picture/scan-image",
        "/pdf/analyze-text",
        "/pdf/create-vocabulary",
        "/pdf/speak",
        "/pdf/cache-ocr-page",
    }:
        limit = ANTI_ROBOT_HEAVY_LIMIT
    ok, retry_after = anti_robot_rate_allowed(f"{verb}:{target}:{client_key}", limit, window_seconds)
    if not ok:
        self.record_security_rate_alert(target, "rate_limited", retry_after)
        self.send_json(429, {
            "ok": False,
            "error": "May chu dang nhan qua nhieu yeu cau. Vui long thu lai sau vai giay.",
            "retry_after": retry_after,
            "reason": "rate_limited",
        })
        return False
    return True

# Added 2026-07-09: keeps invalid worker endpoint floods from consuming request parsing/thread time.
def enforce_worker_endpoint_flood_guard(self, path: str) -> bool:
    if self.is_local_admin_request() or self.auth_admin_light():
        return True
    target = clean(path)
    if not target.startswith("/distributed-worker/"):
        return True
    if target == "/distributed-worker/result":
        return True
    client_key = self.anti_robot_client_key()
    ok, retry_after = anti_robot_rate_allowed(f"WORKER:{target}:{client_key}", ANTI_ROBOT_WORKER_ENDPOINT_LIMIT, 60)
    if ok:
        return True
    self.record_security_rate_alert(target, "worker_endpoint_rate_limited", retry_after)
    self.send_json(429, {
        "ok": False,
        "error": "Worker endpoint dang nhan qua nhieu request tu may nay.",
        "retry_after": retry_after,
        "reason": "worker_endpoint_rate_limited",
    })
    return False

def enforce_anti_robot_challenge(self, path: str, method: str) -> bool:
    if auth_limits_disabled_for_benchmark():
        return True
    if self.is_local_admin_request() or self.auth_admin_light():
        return True
    if method.upper() == "POST" and clean(path) == "/email-routing/inbound" and cloudflare_email_routing_verify_inbound_headers(self.headers):
        return True
    if not anti_robot_browser_like(self.headers, method):
        self.send_json(403, {"ok": False, "error": "Yeu cau bi chan de bao ve may chu.", "reason": "browser_check_failed"})
        return False
    if method.upper() != "POST":
        return True
    token = clean(self.headers.get("X-Future-Anti-Robot", ""))
    ok, reason = verify_anti_robot_token(token, self.anti_robot_client_key())
    if not ok:
        self.send_json(403, {"ok": False, "error": "Vui long tai lai trang de xac minh trinh duyet.", "reason": reason or "anti_robot_required"})
        return False
    return True

def send_html(self, status: int, payload: str):
    data = html_bytes(payload)
    self.send_response(status)
    self.send_header("Content-Type", "text/html; charset=utf-8")
    self.send_header("Content-Length", str(len(data)))
    self.safe_finish_response(data)

def send_bytes(self, status: int, payload: bytes, content_type: str, cache_control: str = "", accept_ranges: bool = False, content_disposition: str = "", etag: str = "", extra_headers: dict | None = None, timing_label: str = ""):
    data = bytes(payload or b"")
    range_header = clean(self.headers.get("Range", ""))
    no_cache_response = bool(re.search(r"\b(no-cache|no-store|max-age=0)\b", cache_control, flags=re.IGNORECASE))
    etag = clean(etag)
    extra_headers = extra_headers if isinstance(extra_headers, dict) else {}
    def write_extra_headers() -> None:
        for header_name, header_value in extra_headers.items():
            name = clean(str(header_name))
            if not name or "\n" in name or "\r" in name or ":" in name:
                continue
            value = clean(str(header_value))
            if "\n" in value or "\r" in value:
                continue
            self.send_header(name, value)
    if status == 200 and etag:
        request_etags = [item.strip() for item in clean(self.headers.get("If-None-Match", "")).split(",") if item.strip()]
        if etag in request_etags or "*" in request_etags:
            self.send_response(304)
            self.send_header("ETag", etag)
            if cache_control:
                self.send_header("Cache-Control", cache_control)
            write_extra_headers()
            queue_wait_ms = self.request_queue_wait_ms()
            write_started = time.perf_counter()
            self.safe_finish_response()
            if clean(timing_label):
                stt_debug_log(
                    clean(timing_label),
                    status=304,
                    bytes=0,
                    ok=True,
                    queue_wait_ms=round(queue_wait_ms, 3),
                    handler_elapsed_ms=round(self.request_handler_elapsed_ms(), 3),
                    write_ms=round((time.perf_counter() - write_started) * 1000, 3),
                )
            return
    if status == 200 and accept_ranges and range_header.startswith("bytes=") and data:
        match = re.match(r"^bytes=(\d*)-(\d*)$", range_header)
        if match:
            start_text, end_text = match.groups()
            start = int(start_text) if start_text else 0
            end = int(end_text) if end_text else len(data) - 1
            start = max(0, min(start, len(data) - 1))
            end = max(start, min(end, len(data) - 1))
            chunk = data[start:end + 1]
            self.send_response(206)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(chunk)))
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
            self.send_header("Accept-Ranges", "bytes")
            if etag:
                self.send_header("ETag", etag)
            if cache_control:
                self.send_header("Cache-Control", cache_control)
                if no_cache_response:
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Expires", "0")
            if content_disposition:
                self.send_header("Content-Disposition", content_disposition)
            write_extra_headers()
            queue_wait_ms = self.request_queue_wait_ms()
            write_started = time.perf_counter()
            self.safe_finish_response(chunk)
            if clean(timing_label):
                stt_debug_log(
                    clean(timing_label),
                    status=206,
                    bytes=len(chunk),
                    ok=True,
                    queue_wait_ms=round(queue_wait_ms, 3),
                    handler_elapsed_ms=round(self.request_handler_elapsed_ms(), 3),
                    write_ms=round((time.perf_counter() - write_started) * 1000, 3),
                )
            return
    gzip_allowed = (
        status == 200
        and not accept_ranges
        and not range_header
        and not clean(extra_headers.get("Content-Encoding", ""))
        and etag
        and len(data) >= 2048
        and "gzip" in clean(self.headers.get("Accept-Encoding", "")).lower()
        and (
            content_type.startswith("text/")
            or "javascript" in content_type
            or "json" in content_type
            or "xml" in content_type
        )
    )
    content_encoding = ""
    if gzip_allowed:
        compressed = gzip_cache_get(f"{etag}:gzip", data)
        if compressed and len(compressed) + 64 < len(data):
            data = compressed
            content_encoding = "gzip"
    self.send_response(status)
    if status >= 400:
        self.close_connection = True
        self.send_header("Connection", "close")
    self.send_header("Content-Type", content_type)
    self.send_header("Content-Length", str(len(data)))
    if content_encoding:
        self.send_header("Content-Encoding", content_encoding)
        self.send_header("Vary", "Accept-Encoding")
    if accept_ranges:
        self.send_header("Accept-Ranges", "bytes")
    if etag:
        self.send_header("ETag", etag)
    if cache_control:
        self.send_header("Cache-Control", cache_control)
        if no_cache_response:
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
    if content_disposition:
        self.send_header("Content-Disposition", content_disposition)
    write_extra_headers()
    queue_wait_ms = self.request_queue_wait_ms()
    write_started = time.perf_counter()
    ok = self.safe_finish_response(data)
    if clean(timing_label):
        stt_debug_log(
            clean(timing_label),
            status=status,
            bytes=len(data),
            ok=bool(ok),
            queue_wait_ms=round(queue_wait_ms, 3),
            handler_elapsed_ms=round(self.request_handler_elapsed_ms(), 3),
            write_ms=round((time.perf_counter() - write_started) * 1000, 3),
        )

def read_json_body(self) -> dict:
    try:
        length = int(self.headers.get("Content-Length", "0"))
    except ValueError:
        length = 0
    if length <= 0:
        return {}
    # Added 2026-07-11: distributed TTS results carry base64 audio, so long Vietnamese clips exceed the normal small JSON cap.
    path = urlparse(getattr(self, "path", "") or "").path.rstrip("/") or "/"
    max_body = 1024 * 1024 * 1024 if path == "/distributed-worker/result" else MAX_JSON_BODY_BYTES
    if length > max_body:
        raise RuntimeError(f"JSON body qua lon, toi da {max_body // 1024}KB.")
    raw = self.rfile.read(length)
    if not raw or not raw.strip():
        return {}
    try:
        payload = json.loads(raw.decode("utf-8-sig", errors="replace"))
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        raise RuntimeError("JSON body khong hop le.") from exc

def is_local_admin_request(self) -> bool:
    host_header = clean(self.headers.get("Host", ""))
    return is_local_client(self.client_address[0]) and request_host_is_private_or_local(host_header)

def auth_session(self) -> dict | None:
    self._auth_error_reason = ""
    token = clean(self.headers.get("Authorization", ""))
    if not token:
        token = clean(self.headers.get("X-Future-Auth", ""))
    if not token:
        token = request_cookie_value(self.headers.get("Cookie", ""), AUTH_COOKIE_NAME)
    if getattr(self, "_auth_session_checked_token", None) == token:
        cached = getattr(self, "_auth_session_checked_value", None)
        self._auth_error_reason = getattr(self, "_auth_session_checked_reason", "")
        return dict(cached) if isinstance(cached, dict) else None
    session, reason = auth_session_state_for_token(token)
    self._auth_session_checked_token = token
    self._auth_session_checked_value = dict(session) if isinstance(session, dict) else None
    self._auth_session_checked_reason = "" if session else reason
    self._auth_error_reason = "" if session else reason
    return session

def speak_skip_admin_session(self) -> dict | None:
    if self.is_local_admin_request():
        return {"username": "server", "is_admin": True, "local": True}
    session = self.auth_session()
    if session and is_admin_user(session.get("username", "")):
        return session
    return None

def auth_admin_session(self) -> dict | None:
    session = self.auth_session()
    if session and is_admin_user(session.get("username", "")):
        return session
    if self.is_local_admin_request():
        return {"username": "server", "is_admin": True, "local": True}
    return None

def do_OPTIONS(self):
    self.send_response(204)
    self.safe_finish_response()
