# Loaded by FUTURE.server_parts.11_http_server into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def do_POST(self):
    self._future_handler_started_at = time.perf_counter()
    self._future_handler_is_first_request = not bool(getattr(self, "_future_handler_seen_request", False))
    self._future_handler_seen_request = True
    path = urlparse(self.path).path.rstrip("/") or "/"
    if not future_worker_listener_allows(self, path, "POST"):
        return
    self.completion_trace_begin(path)
    self.record_security_poll_stat(path, "POST")
    if not self.enforce_security_block(path):
        return
    if path.startswith("/distributed-worker/") and not self.enforce_worker_endpoint_flood_guard(path):
        return
    if path.startswith("/builder/") and self.is_local_admin_request():
        server_data_manifest_build_hold_note_activity(path)
    if path == "/builder/session":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Builder session bridge chi cho may server local."})
            return
        try:
            result = server_data_manifest_builder_session_event(self.read_json_body())
            self.send_json(200, {"ok": True, "build_hold": result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if not (path.startswith("/distributed-worker/") or path.startswith("/builder/")):
        if not self.enforce_anti_robot_rate(path, "POST"):
            return
        if not self.enforce_anti_robot_challenge(path, "POST"):
            return
    if path == "/distributed-worker/register":
        try:
            payload = self.read_json_body()
            payload["_server_listener"] = "lan-8890" if bool(getattr(self.server, "future_worker_only", False)) else "web-8877"
            result = distributed_worker_register(
                payload,
                client_ip=clean(self.client_address[0] if self.client_address else ""),
                user_agent=clean(self.headers.get("User-Agent", "")),
            )
            self.send_json(200, {"ok": True, **result})
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/distributed-worker/poll":
        try:
            payload = self.read_json_body()
            payload["_server_listener"] = "lan-8890" if bool(getattr(self.server, "future_worker_only", False)) else "web-8877"
            wait_seconds = max(0.0, min(30.0, float(payload.get("wait_seconds", 20) or 20)))
            result = distributed_worker_poll(
                payload,
                client_ip=clean(self.client_address[0] if self.client_address else ""),
                user_agent=clean(self.headers.get("User-Agent", "")),
                wait_seconds=wait_seconds,
            )
            self.send_json(200, {"ok": True, **result})
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/distributed-worker/result":
        try:
            payload = self.read_json_body()
            result = distributed_worker_submit_result(payload, client_ip=clean(self.client_address[0] if self.client_address else ""))
            self.send_json(200, {"ok": True, **result})
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/distributed-worker/gemini-key":
        try:
            payload = self.read_json_body()
            result = distributed_worker_gemini_key(payload)
            self.send_json(200, {"ok": True, **result})
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/distributed-worker/log":
        try:
            payload = self.read_json_body()
            result = distributed_worker_submit_log(payload, client_ip=clean(self.client_address[0] if self.client_address else ""))
            self.send_json(200, {"ok": True, **result})
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/dashboard/worker-log-visibility":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi dashboard tren may server moi duoc doi log worker."})
            return
        try:
            payload = self.read_json_body()
            visible = truthy(payload.get("visible", True), True)
            SERVER_STATE["dashboard_worker_access_logs_visible"] = bool(visible)
            self.send_json(200, {"ok": True, "visible": bool(visible)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/builder/translate":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Builder worker bridge chi cho may server local."})
            return
        try:
            payload = self.read_json_body()
            source_text = str(payload.get("text", "") or "")
            target = clean(payload.get("dest", "vi")) or "vi"
            src = clean(payload.get("src", "auto")) or "auto"
            limit = max(1, min(9000, int(float(payload.get("limit", 9000) or 9000))))
            translated = chat_translate_text(source_text, dest=target, src=src, limit=limit, max_wait_seconds=45)
            self.send_json(200, {"ok": True, "translation": translated, "target": target, "src": src})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/builder/tts":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Builder worker bridge chi cho may server local."})
            return
        builder_gate_lock = getattr(self.server, "_future_request_accept_times_lock", None)
        builder_registered = False
        learner_requests = 0
        if builder_gate_lock is not None:
            with builder_gate_lock:
                active_requests = max(0, int(getattr(self.server, "_future_active_requests", 0) or 0))
                active_builder = max(0, int(getattr(self.server, "_future_active_builder_requests", 0) or 0))
                learner_requests = max(0, active_requests - active_builder - 1)
                self.server._future_active_builder_requests = active_builder + 1
                builder_registered = True
        try:
            payload = self.read_json_body()
            source_text = str(payload.get("text", "") or "")
            voice = clean(payload.get("voice", "")) or "kokoro:am_adam"
            throttle_state = durable_tts_background_throttle_state() if callable(globals().get("durable_tts_background_throttle_state")) else {}
            throttle_for_users = learner_requests > 0 or bool(throttle_state.get("cpu_high"))
            # Added 2026-08-02: serialize durable builder enqueues only while learner traffic is active.
            def submit_builder_job():
                return durable_tts_submit_raw(
                    source_text,
                    voice,
                    priority=3,
                    source=clean(payload.get("source", "")) or "builder_tts",
                    # Keep builder HTTP occupancy short while learner traffic or high CPU is active.
                    # The durable P3 job remains queued and retries reuse its build_id.
                    timeout_seconds=0 if throttle_for_users else 8,
                    build_id=clean(payload.get("build_id", payload.get("buildId", ""))),
                    params={"timeout_seconds": 0 if voice.lower().startswith("kokoro_vi:") else 90},
                )
            if throttle_for_users:
                with BUILDER_TTS_ENQUEUE_LOCK:
                    raw = submit_builder_job()
            else:
                raw = submit_builder_job()
            if raw:
                audio_bytes = raw.get("audio_bytes") or b""
                mime = clean(raw.get("audio_mime", "")) or clean(raw.get("mime", "")) or "audio/mpeg"
                self.send_json(200, {
                    "ok": True,
                    "audio_base64": base64.b64encode(bytes(audio_bytes)).decode("ascii"),
                    "mime": mime,
                    "voice": clean(raw.get("voice", "")) or voice,
                    "worker": clean(raw.get("worker_id", "")) or "distributed",
                })
                return
            self.send_json(503, {"ok": False, "queued": True, "throttled_for_users": bool(throttle_for_users), "learner_requests": learner_requests, "error": "Builder TTS is queued; retry will reuse the same durable job."})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        finally:
            if builder_registered and builder_gate_lock is not None:
                with builder_gate_lock:
                    self.server._future_active_builder_requests = max(0, int(getattr(self.server, "_future_active_builder_requests", 1) or 1) - 1)
        return
    if path == "/builder/phonemize":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Builder phonemize bridge chi cho may server local."})
            return
        try:
            payload = self.read_json_body()
            source_text = str(payload.get("text", "") or "")
            voice = clean(payload.get("voice", "en-US")) or "en-US"
            ipa = ""
            worker_name = ""
            try:
                ipa = distributed_worker_try_phonemize(source_text, voice, timeout_seconds=25)
                if ipa:
                    worker_name = "distributed"
            except Exception as exc:
                stt_debug_log("builder_distributed_phonemize_fallback", voice=voice, error=str(exc))
            if not ipa:
                old_bridge_disabled = os.environ.get("FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED", "")
                os.environ["FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED"] = "1"
                try:
                    import future_lesson_builder_gui as builder  # type: ignore

                    ipa = builder.phonemize_text(source_text, voice)
                finally:
                    if old_bridge_disabled:
                        os.environ["FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED"] = old_bridge_disabled
                    else:
                        os.environ.pop("FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED", None)
                worker_name = "server-local"
            self.send_json(200, {"ok": True, "ipa": ipa, "voice": voice, "worker": worker_name})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/email-routing/inbound":
        if not (self.is_local_admin_request() or cloudflare_email_routing_verify_inbound_headers(self.headers)):
            self.send_json(403, {"ok": False, "error": "Email inbound secret is invalid."})
            return
        try:
            payload = self.read_json_body()
            result = cloudflare_email_routing_store_message(payload, self.headers)
            self.send_json(202, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path in ("/dashboard/open", "/dashboard/ping", "/dashboard/close", "/dashboard/shutdown"):
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi dashboard tren may server moi duoc dieu khien server."})
            return
        payload = self.read_json_body()
        session_id = clean(payload.get("session", ""))
        if path == "/dashboard/open":
            mark_dashboard_open(session_id)
            self.send_json(200, {"ok": True, **dashboard_control_response(session_id)})
            return
        if path == "/dashboard/ping":
            mark_dashboard_ping(session_id)
            self.send_json(200, {"ok": True, **dashboard_control_response(session_id)})
            return
        if path == "/dashboard/shutdown":
            accepted = mark_dashboard_close(session_id)
            if not accepted:
                self.send_json(409, {"ok": False, "accepted": False, "error": "Dashboard session is no longer active.", **dashboard_control_response(session_id)})
                return
            self.send_json(202, {"ok": True, "accepted": True, **dashboard_control_response(session_id)})
            request_server_shutdown("dashboard_manual_close", delay=0.75)
            return
        accepted = mark_dashboard_close(session_id)
        self.send_json(202, {"ok": True, "accepted": accepted, **dashboard_control_response(session_id)})
        if accepted:
            request_server_shutdown("dashboard_close", delay=0.75)
        return
    if path == "/dashboard/security/block":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Security block chi mo tren may server."})
            return
        try:
            payload = self.read_json_body()
            result = security_block_poll_identity(payload.get("type", payload.get("identity_type", "")), payload.get("identity", ""), payload.get("minutes", 10))
            self.send_json(200, {"ok": True, **result, "security_poll": security_poll_dashboard_snapshot(12), "security_alerts": security_rate_alerts_snapshot(20)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/dashboard/users/password":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi dashboard tren may server moi duoc doi mat khau user."})
            return
        try:
            payload = self.read_json_body()
            result = admin_change_user_password(payload.get("username", ""), str(payload.get("password", "") or ""))
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/dashboard/users/block-login":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi dashboard tren may server moi duoc chan dang nhap user."})
            return
        try:
            payload = self.read_json_body()
            result = set_user_login_blocked(payload.get("username", ""), truthy(payload.get("blocked", True), True))
            self.send_json(200, {"ok": True, **result, **dashboard_admin_payload()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/dashboard/kill-other-servers":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi dashboard tren may server moi duoc kill server cu."})
            return
        try:
            payload = self.read_json_body()
            session_id = clean(payload.get("session", ""))
            if session_id:
                keep_dashboard_session(session_id)
            result = kill_other_future_servers()
            self.send_json(200, {"ok": True, **result, **dashboard_control_response(session_id)})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/dashboard/clean-close-all":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi dashboard tren may server moi duoc dong Future server va tunnel."})
            return
        try:
            payload = self.read_json_body()
            session_id = clean(payload.get("session", ""))
            result_preview = {
                "current_pid": os.getpid(),
                "targets": [
                    {"pid": int(row.get("pid", 0) or 0), "name": clean(row.get("name", "")), "current": bool(row.get("current"))}
                    for row in list_future_runtime_processes_for_clean_close()
                ],
            }
            self.send_json(202, {"ok": True, "accepted": True, **result_preview, **dashboard_control_response(session_id)})
            schedule_clean_close_all_future_runtime("dashboard_clean_close_all", delay=0.45)
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/frontend-version/bump":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Only the server dashboard can update connected clients."})
            return
        try:
            payload = self.read_json_body()
            result = bump_frontend_reload_state(
                payload.get("reason", "dashboard_update"),
                payload.get("command", ""),
            )
            self.send_json(200, {"ok": True, **result, **frontend_delivery_signature()})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/dashboard/admins":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Admin settings are only available on the server machine."})
            return
        try:
            payload = self.read_json_body()
            result = set_admin_user(payload.get("username", ""), truthy(payload.get("enabled", True), True))
            self.send_json(200, {"ok": True, **result, **dashboard_admin_payload()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path in (
        "/dashboard/email-routing/config",
        "/dashboard/email-routing/destination",
        "/dashboard/email-routing/alias",
        "/dashboard/email-routing/delete-rule",
    ):
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Email Routing is only available on the server machine."})
            return
        try:
            payload = self.read_json_body()
            if path == "/dashboard/email-routing/config":
                result = cloudflare_email_routing_save_settings(payload)
            elif path == "/dashboard/email-routing/destination":
                result = cloudflare_email_routing_create_destination(payload)
            elif path == "/dashboard/email-routing/alias":
                result = cloudflare_email_routing_create_alias(payload)
            else:
                result = cloudflare_email_routing_delete_alias(payload)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/dashboard/users/delete":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "User deletion is only available on the server machine."})
            return
        try:
            payload = self.read_json_body()
            username = normalize_username(payload.get("username", ""))
            confirm = normalize_username(payload.get("confirm", ""))
            if not username or confirm != username:
                raise RuntimeError("Nhap lai dung username de xac nhan xoa.")
            result = delete_user_data(username)
            self.send_json(200, {"ok": True, "deleted": result, **dashboard_admin_payload()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf-metadata/warm":
        session = self.auth_session()
        if not self.is_local_admin_request() and not (session and is_admin_user(session.get("username", ""))):
            self.send_json(403, {"ok": False, "error": "Only admin can warm PDF metadata index."})
            return
        start_pdf_picture_metadata_warmer(force=True)
        self.send_json(202, {"ok": True, **pdf_picture_metadata_status()})
        return
    if path == "/lesson-stats/refresh":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            payload = self.read_json_body()
            target_user = normalize_username(payload.get("user", "") or payload.get("username", "") or username)
            if target_user != username and not is_admin_user(username):
                self.send_json(403, {"ok": False, "error": "Only admins can refresh another user's learning stats."})
                return
            stats = lesson_user_learning_summary(target_user, force=True)
            self.send_json(200, {"ok": True, "username": target_user, "learning_stats": stats})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/qmdict/reload":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "QmDict reload is only available on the server machine."})
            return
        try:
            reload_result = reload_qmdict_runtime(force=True, reason="dashboard")
            vocab_sync = start_main_vocab_sync_all(force=True, reason="qmdict-dashboard-reload")
            self.send_json(
                200,
                {
                    "ok": True,
                    "qmdict_reload": reload_result,
                    "vocabulary_sync": vocab_sync,
                    "audio_refresh": qmdict_audio_refresh_job_snapshot(),
                },
            )
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/qmdict/meaning-audio-refresh":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "QmDict Vietnamese audio refresh is only available on the server machine."})
            return
        try:
            payload = self.read_json_body()
            mode = clean(payload.get("mode", "missing")) or "missing"
            self.send_json(202, {"ok": True, **start_qmdict_meaning_audio_refresh(payload.get("keys"), mode=mode)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/qmdict/meaning-audio-refresh/cancel":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "QmDict Vietnamese audio refresh cancel is only available on the server machine."})
            return
        with QMDICT_AUDIO_REFRESH_LOCK:
            if not QMDICT_AUDIO_REFRESH_JOB.get("running"):
                self.send_json(200, {"ok": True, "cancelled": False, "audio_refresh": dict(QMDICT_AUDIO_REFRESH_JOB)})
                return
            QMDICT_AUDIO_REFRESH_JOB["cancel_requested"] = True
            QMDICT_AUDIO_REFRESH_JOB["message"] = "Cancelling Vietnamese audio refresh."
            QMDICT_AUDIO_REFRESH_JOB["updated_at"] = utc_timestamp()
            snapshot = dict(QMDICT_AUDIO_REFRESH_JOB)
        write_qmdict_audio_refresh_progress({"version": 1, **snapshot})
        self.send_json(202, {"ok": True, "cancelled": True, "audio_refresh": snapshot})
        return
    if path == "/space-v/repair-qmdict":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Space_V repair is only available on the server machine."})
            return
        try:
            self.send_json(202, {"ok": True, **start_space_v_qmdict_repair()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/qmdict/word-audio-refresh":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "QmDict word audio refresh is only available on the server machine."})
            return
        try:
            payload = self.read_json_body()
            self.send_json(202, {"ok": True, **start_qmdict_word_audio_refresh(payload.get("mode", "all"), payload.get("items"))})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/qmdict/word-audio-refresh/cancel":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "QmDict word audio refresh cancel is only available on the server machine."})
            return
        try:
            with QMDICT_WORD_AUDIO_REFRESH_LOCK:
                if not QMDICT_WORD_AUDIO_REFRESH_JOB.get("running"):
                    self.send_json(200, {"ok": True, "cancelled": False, "word_audio_refresh": dict(QMDICT_WORD_AUDIO_REFRESH_JOB)})
                    return
                QMDICT_WORD_AUDIO_REFRESH_JOB["cancel_requested"] = True
                QMDICT_WORD_AUDIO_REFRESH_JOB["message"] = "Cancelling QmDict UK/US word audio refresh."
                QMDICT_WORD_AUDIO_REFRESH_JOB["updated_at"] = utc_timestamp()
                snapshot = dict(QMDICT_WORD_AUDIO_REFRESH_JOB)
            write_qmdict_word_audio_refresh_progress({"version": 1, **snapshot})
            self.send_json(202, {"ok": True, "cancelled": True, "word_audio_refresh": snapshot})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-v/refresh-audio":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            payload = self.read_json_body()
            result = refresh_space_v_word_audio(username, payload.get("word", ""), payload.get("voice", ""))
            self.send_json(200, {"ok": True, **result})
        except SpaceVAudioRefreshRateLimitError as exc:
            self.send_json(429, {"ok": False, "error": str(exc), "retry_after": int(exc.retry_after)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/qmdict/update":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            if not is_admin_user(username):
                self.send_json(403, {"ok": False, "error": "Only admins can edit QmDict."})
                return
            payload = self.read_json_body()
            result = update_qmdict_meaning_type(
                payload.get("word", ""),
                meaning=payload.get("meaning") if "meaning" in payload else None,
                word_type=payload.get("type") if "type" in payload else None,
                usage=payload.get("usage") if "usage" in payload else None,
                examples=payload.get("examples") if "examples" in payload else None,
                source=payload.get("source", ""),
                admin=username,
            )
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            try:
                payload = locals().get("payload", {})
                stt_debug_log(
                    "pdf_ocr_failed",
                    username=locals().get("username", ""),
                    path=locals().get("rel_path", ""),
                    page=(payload.get("page", 1) if isinstance(payload, dict) else 1),
                    rect=(payload.get("rect", {}) if isinstance(payload, dict) else {}),
                    error=str(exc),
                )
            except Exception:
                pass
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/ocr":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = session.get("username", "")
            if not enforce_user_heavy_quota_response(self, username, "ocr"):
                return
            payload = self.read_json_body()
            rel_path = clean_path_value(payload.get("path", ""))
            result = ocr_pdf_region(
                rel_path,
                username,
                admin=is_admin_user(username),
                page=payload.get("page", 1),
                rect=payload.get("rect", {}),
                zoom=payload.get("scale", payload.get("zoom", 2.4)),
            )
            result["vocabulary"] = qmdict_vocabulary_stats_queued(result.get("text", ""), username)
            chat_mark_online(username)
            mark_user_activity(username, {
                "status": "Ghost Eye PDF region",
                "space": "Space_PDF",
                "path": rel_path,
                "page": result.get("page", 1),
            })
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/picture/ocr":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = session.get("username", "")
            if not enforce_user_heavy_quota_response(self, username, "ocr"):
                return
            payload = self.read_json_body()
            rel_path = clean_path_value(payload.get("path", ""))
            result = ocr_picture_region(
                rel_path,
                username,
                admin=is_admin_user(username),
                page=payload.get("page", 1),
                rect=payload.get("rect", {}),
            )
            result["vocabulary"] = qmdict_vocabulary_stats_queued(result.get("text", ""), username)
            chat_mark_online(username)
            mark_user_activity(username, {
                "status": "Ghost Eye picture region",
                "space": "Space_Picture",
                "path": rel_path,
                "page": result.get("page", 1),
            })
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/scan-page":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = session.get("username", "")
            if not enforce_user_heavy_quota_response(self, username, "ocr"):
                return
            payload = self.read_json_body()
            rel_path = clean_path_value(payload.get("path", ""))
            result = pdf_scan_page_vocabulary(
                rel_path,
                username,
                admin=is_admin_user(username),
                page=payload.get("page", 1),
            )
            chat_mark_online(username)
            mark_user_activity(username, {
                "status": "Ghost Eye full page",
                "space": "Space_PDF",
                "path": rel_path,
                "page": result.get("page", 1),
            })
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/picture/scan-image":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = session.get("username", "")
            if not enforce_user_heavy_quota_response(self, username, "ocr"):
                return
            payload = self.read_json_body()
            rel_path = clean_path_value(payload.get("path", ""))
            result = picture_scan_vocabulary(
                rel_path,
                username,
                admin=is_admin_user(username),
                page=payload.get("page", 1),
            )
            chat_mark_online(username)
            mark_user_activity(username, {
                "status": "Ghost Eye full picture",
                "space": "Space_Picture",
                "path": rel_path,
                "page": result.get("page", 1),
            })
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/cache-ocr-page":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            if not enforce_user_heavy_quota_response(self, username, "ocr"):
                return
            payload = self.read_json_body()
            rel_path = clean_path_value(payload.get("path", ""))
            mode = "picture" if clean(payload.get("mode", "")).lower() == "picture" else "pdf"
            cache_hints = [
                payload.get("name", ""),
                payload.get("title", ""),
                payload.get("folder", ""),
                payload.get("image", ""),
            ]
            stt_debug_log(
                "pdf_cache_ocr_request",
                username=username,
                path=rel_path,
                mode=mode,
                page=payload.get("page", 1),
                name=clean(payload.get("name", "")),
                title=clean(payload.get("title", "")),
                folder=clean(payload.get("folder", "")),
                image=clean(payload.get("image", "")),
            )
            result = pdf_cache_ocr_page_text(
                rel_path,
                username,
                admin=is_admin_user(username),
                page=payload.get("page", 1),
                mode=mode,
                hints=cache_hints,
            )
            stt_debug_log(
                "pdf_cache_ocr_result",
                username=username,
                path=rel_path,
                mode=mode,
                page=result.get("page", payload.get("page", 1)),
                cache_hit=bool(result.get("cache_hit")),
                reason=clean(result.get("reason", "")),
                cache_folder=clean(result.get("cache_folder", "")),
                cache_file=clean(result.get("cache_file", "")),
                candidates=(result.get("candidates") or [])[:8],
            )
            if result.get("cache_hit"):
                result["vocabulary"] = qmdict_vocabulary_stats_queued(result.get("text", ""), username)
                chat_mark_online(username)
                mark_user_activity(username, {
                    "status": "Ghost Eye cache OCR page",
                    "space": "Space_Picture" if mode == "picture" else "Space_PDF",
                    "path": rel_path,
                    "page": result.get("page", 1),
                })
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            try:
                stt_debug_log(
                    "pdf_cache_ocr_exception",
                    username=locals().get("username", ""),
                    path=locals().get("rel_path", ""),
                    error=str(exc),
                    traceback=traceback.format_exc(),
                )
            except Exception:
                pass
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/analyze-text":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            if not enforce_user_heavy_quota_response(self, username, "ocr"):
                return
            payload = self.read_json_body()
            text = lesson_task_notice_text(payload.get("text", ""), limit=24000)
            rel_path = clean_path_value(payload.get("path", ""))
            page = max(1, int(payload.get("page", 1) or 1))
            vocabulary = qmdict_vocabulary_stats_queued(text, username)
            chat_mark_online(username)
            if rel_path:
                mark_user_activity(username, {
                    "status": "Ghost Eye edited text",
                    "space": "Space_PDF" if Path(rel_path).suffix.lower() == ".pdf" else "Space_Picture",
                    "path": rel_path,
                    "page": page,
                })
            self.send_json(200, {"ok": True, "text": text, "page": page, "vocabulary": vocabulary})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/create-vocabulary":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = session.get("username", "")
            if not enforce_user_heavy_quota_response(self, username, "ocr"):
                return
            payload = self.read_json_body()
            rel_path = clean_path_value(payload.get("path", ""))
            result = build_pdf_vocab_mission(
                rel_path,
                username,
                page=payload.get("page", 1),
                text=payload.get("text", ""),
                include_known=bool(payload.get("include_known") or payload.get("force_words")),
                source=payload.get("source", ""),
                word_items=payload.get("word_items", []),
            )
            chat_mark_online(username)
            mark_user_activity(username, {
                "status": "Created PDF vocabulary",
                "space": "Space_PDF",
                "path": rel_path,
                "page": result.get("page", 1),
            })
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/translate":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            if not enforce_user_heavy_quota_response(self, username, "translate"):
                return
            payload = self.read_json_body()
            source_text = lesson_task_notice_text(payload.get("text", ""), limit=9000)
            target = clean(payload.get("target", payload.get("dest", "vi"))).lower()
            src = clean(payload.get("source", payload.get("src", "auto"))).lower()
            if target not in {"vi", "en"}:
                target = "vi"
            if not source_text:
                raise RuntimeError("Text to Explore is empty.")
            try:
                translated = chat_translate_text(source_text, dest=target, src=src if src in {"vi", "en"} else "auto", limit=9000)
            except Exception:
                if target == "vi":
                    translated = request_gemini_vietnamese_translation(source_text, structured=True)
                else:
                    translated = ""
            if not clean(translated):
                raise RuntimeError("Khong dich duoc van ban bang bo dich hien tai.")
            self.send_json(200, {"ok": True, "text": source_text, "target": target, "translated": translated})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/speak":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            payload = self.read_json_body()
            text = sanitize_pdf_voice_text(payload.get("text", ""), limit=1400)
            voice = clean(payload.get("voice", "")) or "kokoro:am_adam"
            client_source = clean(payload.get("client_source", payload.get("clientSource", ""))).lower()
            if not re.match(r"^(kokoro|kokoro_vi|sot|edge|microsoft):[A-Za-z0-9._:\-]+$", voice):
                voice = "kokoro:am_adam"
            if not text:
                raise RuntimeError("Text to explore is empty.")
            cached_audio = qmlearn_cached_word_audio_payload(text, voice)
            if cached_audio:
                self.send_json(200, {"ok": True, "text": text, **cached_audio})
                return
            interactive_lesson_audio = client_source in {"lesson_audio", "space_v_audio", "space_w_audio"} and len(text) <= 240
            if not interactive_lesson_audio and not enforce_user_heavy_quota_response(self, username, "tts"):
                return
            try:
                audio_payload = chat_synthesize_message_audio_queued(
                    text,
                    voice,
                    source="interactive_lesson_audio" if interactive_lesson_audio else "runtime_voice",
                )
            except Exception as generation_exc:
                self.send_json(503, {
                    "ok": False,
                    "error": str(generation_exc),
                    "reason": "tts_all_generation_failed",
                    "worker_attempted": True,
                    "server_fallback_attempted": True,
                    "browser_fallback_allowed": True,
                })
                return
            self.send_json(200, {"ok": True, "text": text, **audio_payload})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/speak-training/reference":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            if not enforce_user_heavy_quota_response(self, username, "tts"):
                return
            payload = self.read_json_body()
            text = lesson_task_notice_text(payload.get("text", ""), limit=6000)
            if not text:
                raise RuntimeError("Text to Explore is empty.")
            self.send_json(200, {"ok": True, "speech_training": build_speech_reference_payload_worker(text)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/ai-agent/history":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            payload = self.read_json_body()
            action = clean(payload.get("action", "save")).lower()
            if action in {"list", "load"}:
                limit = space_w_int(payload.get("limit", 80), 80)
                self.send_json(200, {"ok": True, "history": list_ai_agent_history(username, limit)})
                return
            if action in {"remove", "delete"}:
                result = remove_ai_agent_history(username, payload.get("id", ""))
                self.send_json(200, {"ok": True, **result})
                return
            entry = save_ai_agent_history(username, payload)
            self.send_json(200, {"ok": True, "entry": entry, "history": list_ai_agent_history(username, 80)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/ai-agent/space-p/followup":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            chat_mark_online(username)
            touch_user_activity_seen(username)
            payload = self.read_json_body()
            context = payload.get("context", {}) if isinstance(payload.get("context", {}), dict) else {}
            result = build_ai_agent_space_p_followup(username, context=context)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/ai-agent/ask":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if not enforce_user_heavy_quota_response(self, username, "gemini"):
                return
            payload = self.read_json_body()
            message = lesson_task_notice_text(payload.get("message", payload.get("text", "")), limit=3600)
            mode = normalize_ai_agent_answer_mode(payload.get("mode", payload.get("answer_mode", payload.get("answerMode", "spoken"))))
            context = payload.get("context", {}) if isinstance(payload.get("context", {}), dict) else {}
            notice = build_ai_agent_notice(username, message, context=context, mode=mode)
            self.send_json(200, {"ok": True, "notice": notice, "answer_en": notice.get("translation_en") or notice.get("text", ""), "answer_vi": notice.get("translation_vi", "")})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/ai-agent/translate":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if not enforce_user_heavy_quota_response(self, username, "gemini"):
                return
            payload = self.read_json_body()
            source_text = lesson_task_notice_text(payload.get("message", payload.get("text", "")), limit=3600)
            target = clean(payload.get("target", payload.get("dest", "en"))).lower()
            src = clean(payload.get("source", payload.get("src", "auto"))).lower()
            force_translate = truthy(payload.get("force", payload.get("force_translate", payload.get("forceTranslate", False))), False)
            if target not in {"vi", "en"}:
                target = "en"
            if not source_text:
                raise RuntimeError("Text is empty.")
            try:
                translated = chat_translate_text(source_text, dest=target, src=src if src in {"vi", "en"} else "auto", limit=3600, max_wait_seconds=120, force_refresh=force_translate)
            except Exception:
                translated = request_gemini_vietnamese_translation(source_text, structured=True) if target == "vi" else ""
            if not clean(translated):
                raise RuntimeError("Khong dich duoc van ban bang bo dich hien tai.")
            vocabulary = qmdict_vocabulary_stats_queued(translated, username) if target == "en" else {}
            self.send_json(200, {
                "ok": True,
                "text": source_text,
                "source": source_text,
                "target": target,
                "translation": translated,
                "translated": translated,
                "forced": force_translate,
                "vocabulary": vocabulary,
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/word-agent/ask":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if not enforce_user_heavy_quota_response(self, username, "translate"):
                return
            payload = self.read_json_body()
            raw_detail = payload.get("detail") if isinstance(payload.get("detail"), dict) else payload
            detail = normalize_word_agent_detail(raw_detail)
            word = lesson_task_notice_text(payload.get("word") or detail.get("word") or detail.get("surface"), limit=180)
            if not word:
                self.send_json(400, {"ok": False, "error": "Missing word or phrase."})
                return
            page = space_w_int(payload.get("page", 0), 0)
            source = {
                "space": clean(payload.get("space", ""))[:80],
                "file": clean_path_value(payload.get("file", ""))[:420],
                "title": lesson_task_notice_text(payload.get("title", ""), limit=220),
                "page": page,
            }
            question = lesson_task_notice_text(payload.get("question", ""), limit=1200)
            result = request_gemini_word_vietnamese_explanation(
                word=word,
                detail=detail,
                username=username,
                question=question,
                source=source,
            )
            entry = save_word_agent_history({
                "word": word,
                "surface": payload.get("surface") or detail.get("surface"),
                "kind": detail.get("kind"),
                "username": username,
                "question": question or f"Explain {word}",
                "answer_vi": result.get("answer_vi", ""),
                "model": result.get("model", ""),
                "detail": detail,
                **source,
            })
            self.send_json(200, {
                "ok": True,
                **result,
                "entry": entry,
                "history": list_word_agent_history(word, 80),
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/phonetic/ipa":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            term = lesson_task_notice_text(payload.get("term") or payload.get("word") or payload.get("text"), limit=160)
            if not term:
                self.send_json(400, {"ok": False, "error": "Missing word or phrase."})
                return
            entry = get_or_create_phonetic_ipa_queued(term, generate=True)
            self.send_json(200, {
                "ok": True,
                "key": phonetic_ipa_key(term),
                "entry": entry,
                "phonetic_ipa": {entry.get("key"): entry} if isinstance(entry, dict) and entry.get("key") else {},
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/agent-explain":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if not enforce_user_heavy_quota_response(self, username, "gemini"):
                return
            payload = self.read_json_body()
            text = lesson_task_notice_text(payload.get("text", ""), limit=9000)
            if not text:
                self.send_json(400, {"ok": False, "error": "Text to Explore is empty."})
                return
            page = 0
            try:
                page = int(payload.get("page", 0) or 0)
            except Exception:
                page = 0
            result = request_gemini_pdf_vietnamese_explanation(
                question=payload.get("question", ""),
                text=text,
                username=username,
                title=payload.get("title", ""),
                page=page,
            )
            entry_title_source = lesson_task_notice_text(payload.get("question", ""), limit=90) or "Ghost Eye explanation"
            pdf_title = lesson_task_notice_text(payload.get("title", ""), limit=90)
            source_path = clean_path_value(payload.get("path", ""))
            source_space = "space_picture" if Path(source_path).suffix.lower() in IMAGE_FILE_SUFFIXES else "space_pdf"
            history_entry = save_ai_agent_history(username, {
                "title": f"{pdf_title or 'PDF'} p.{page or '?'} | {entry_title_source}",
                "answer_vi": result.get("answer_vi", ""),
                "user_prompt": payload.get("question", ""),
                "space": source_space,
                "file": source_path,
                "context": {
                    "kind": "space_picture_ghost_eye" if source_space == "space_picture" else "space_pdf_ghost_eye",
                    "pdf_title": pdf_title,
                    "pdf_page": page,
                    "text_to_explore": lesson_task_notice_text(text, limit=2200),
                },
            })
            self.send_json(200, {"ok": True, **result, "history_entry": history_entry})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/lesson-task-notices":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            payload = self.read_json_body()
            action = clean(payload.get("action", "")).lower()
            if action in {"read", "ack", "acknowledge"}:
                result = mark_lesson_task_notice_read(username, payload.get("id", ""))
                self.send_json(200, {"ok": True, "task_owner": username, **result})
                return
            if action in {"seen", "view", "viewed"}:
                result = mark_lesson_task_notice_seen(username, payload.get("id", ""))
                self.send_json(200, {"ok": True, "task_owner": username, **result})
                return
            if not is_admin_user(username):
                self.send_json(403, {"ok": False, "error": "Only admins can edit task notices."})
                return
            if action in {"translate", "translate_notice", "task_translate"}:
                source_text = lesson_task_notice_text(payload.get("text", ""))
                target = clean(payload.get("target", payload.get("dest", ""))).lower()
                src = clean(payload.get("source", payload.get("src", "auto"))).lower()
                if target not in {"vi", "en"}:
                    raise RuntimeError("Target language must be vi or en.")
                if not source_text:
                    raise RuntimeError("Text is empty.")
                translated = chat_translate_text(source_text, dest=target, src=src if src in {"vi", "en"} else "auto")
                self.send_json(200, {"ok": True, "translation": translated, "target": target, "source": src or "auto"})
                return
            target_user = normalize_username(payload.get("user", "") or payload.get("target_user", ""))
            if action in {"remove", "delete"}:
                result = remove_lesson_task_notice(target_user, payload.get("id", ""))
            elif action in {"send", "send_now", "immediate", "now"}:
                notice = build_lesson_task_notice_record(target_user, payload, username, transient=True)
                result = queue_lesson_task_notice_immediate(target_user, notice)
                result["notice"] = result.get("immediate_notice", {})
                result["task_notices"] = lesson_task_notices_for_user(target_user, admin_view=True)
                result["target_online"] = user_recently_online(target_user)
                result["target_user"] = target_user
            else:
                result = save_lesson_task_notice(target_user, payload, username)
            self.send_json(200, {"ok": True, "task_owner": target_user, "admin": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/lesson-task-notice-avatar":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            if not is_admin_user(username):
                self.send_json(403, {"ok": False, "error": "Only admins can upload task notice avatars."})
                return
            _fields, files = parse_multipart_form(self.headers, self.rfile, max_bytes=9 * 1024 * 1024)
            upload = files.get("file") or files.get("avatar") or (next(iter(files.values())) if files else None)
            if not upload:
                raise RuntimeError("No avatar file selected.")
            result = save_lesson_task_notice_avatar(upload, username)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/avatar":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            _fields, files = parse_multipart_form(self.headers, self.rfile, max_bytes=11 * 1024 * 1024)
            upload = files.get("file") or files.get("avatar") or (next(iter(files.values())) if files else None)
            if not upload:
                raise RuntimeError("No avatar file selected.")
            result = save_user_avatar(upload, username)
            self.send_json(200, {"ok": True, "username": username, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/profile-photo":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            fields, files = parse_multipart_form(self.headers, self.rfile, max_bytes=19 * 1024 * 1024)
            upload = files.get("file") or files.get("photo") or (next(iter(files.values())) if files else None)
            if not upload:
                raise RuntimeError("No profile photo selected.")
            try:
                slot = int(clean(fields.get("slot", "-1")) or -1)
            except Exception:
                slot = -1
            result = save_user_profile_photo(upload, username, slot=slot)
            self.send_json(200, {"ok": True, "username": username, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/profile-card":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            payload = self.read_json_body()
            result = save_user_profile_card(username, payload)
            self.send_json(200, {"ok": True, "username": username, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/lesson-tasks":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            viewer_is_admin = is_admin_user(username)
            payload = self.read_json_body()
            action = clean(payload.get("action", "")).lower()
            target_user = normalize_username(payload.get("user", "") or payload.get("target_user", "") or username)
            if target_user != username and not viewer_is_admin:
                self.send_json(403, {"ok": False, "error": "Only admins can edit another user's lesson tasks."})
                return
            if action == "add":
                creator_role = "admin" if viewer_is_admin and target_user != username else "user"
                result = add_lesson_task(
                    target_user,
                    payload.get("path", ""),
                    username,
                    payload.get("severity", "normal"),
                    creator_role,
                    effective_path=payload.get("effective_path", ""),
                    link_target=payload.get("link_target", ""),
                    title=payload.get("title", ""),
                    name=payload.get("name", ""),
                    folder_id=payload.get("folder_id", ""),
                    folder_path=payload.get("folder_path", payload.get("folder", "")),
                )
                invalidate_space_task_payload_cache(target_user)
            elif action in {"severity", "priority", "update"}:
                if not viewer_is_admin:
                    self.send_json(403, {"ok": False, "error": "Only admins can change task severity."})
                    return
                result = update_lesson_task_severity(
                    target_user,
                    payload.get("id", ""),
                    payload.get("path", ""),
                    payload.get("severity", "normal"),
                    username,
                )
                invalidate_space_task_payload_cache(target_user)
            elif action in {"remove", "delete"}:
                result = remove_space_task_group(
                    target_user,
                    relative_path=payload.get("path", ""),
                    task_id=payload.get("id", ""),
                    folder_group_key=payload.get("folder_group_key", ""),
                    folder_path=payload.get("folder_path", payload.get("folder", "")),
                    actor_username=username,
                    base_revision=payload.get("baseRevision") if "baseRevision" in payload else None,
                )
                invalidate_space_task_payload_cache(target_user)
            elif action in {"space-folders", "space_folders", "space-task-folders", "space_task_folders"}:
                folder_source = payload.get("folders", payload.get("preferred_folders", payload.get("folder_text", "")))
                settings_result = save_space_task_settings(
                    target_user,
                    folder_source,
                    username,
                    allow_any_top=viewer_is_admin,
                    base_revision=payload.get("baseRevision") if "baseRevision" in payload else None,
                )
                if settings_result.get("changed"):
                    invalidate_space_task_payload_cache(target_user)
                    # ACK the durable SQLite setting immediately; derived task
                    # discovery runs in the bounded shared pool.
                    space_task = queue_space_task_payload_refresh_for_user(
                        target_user,
                        username,
                        include_admin=viewer_is_admin,
                    )
                    result = {"space_task": space_task, "space_tasks": space_task.get("tasks", [])}
                else:
                    # Exact retries are durable no-ops: return the new revision
                    # without invalidating or rebuilding any derived payload.
                    space_task = {
                        "enabled": bool(settings_result.get("preferred_folders")),
                        **settings_result,
                        "tasks": [],
                        "pending": False,
                        "stale": False,
                    }
                    result = {
                        "space_task": space_task,
                        "space_tasks": [],
                        "duplicate": True,
                        "changed": False,
                    }
            else:
                raise RuntimeError("Unknown lesson task action.")
            response = {"ok": True, "task_owner": target_user, "admin": viewer_is_admin, **result}
            cached_stats = read_cached_lesson_user_learning_summary(target_user)
            if cached_stats:
                response["learning_stats"] = cached_stats
            self.send_json(200, response)
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/server-data/op":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            result = server_data_operation(self.read_json_body(), username)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/server-data/manifest-refresh":
        try:
            session = self.auth_session()
            local_admin = self.is_local_admin_request()
            if not session and not local_admin:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", "")) if session else ""
            if session and not is_admin_user(username) and not local_admin:
                self.send_json(403, {"ok": False, "error": "Only admins can refresh the lesson manifest."})
                return
            source = self.read_json_body()
            if truthy(source.get("apply_pending"), False):
                status = apply_server_data_manifest_build_hold("admin-apply")
                self.send_json(202, {"ok": True, "mode": "apply-pending", "accepted": True, "build_hold": status})
                return
            refresh_paths = [
                clean_path_value(item)
                for item in (source.get("paths") if isinstance(source.get("paths"), list) else [])
                if clean_path_value(item)
            ][:200]
            manifest = refresh_server_data_manifest_paths_now(refresh_paths, "manual-paths") if refresh_paths else refresh_server_data_manifest_now("manual")
            folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
            self.send_json(200, {
                "ok": True,
                "mode": "paths" if refresh_paths else "full",
                "paths": refresh_paths,
                "updated_at": clean(manifest.get("updated_at", "")),
                "signature": server_data_manifest_runtime_revision(manifest),
                "integrity_signature": clean(manifest.get("signature", "")),
                "folder_count": len(folders),
                "entry_count": sum(len(rows) for rows in folders.values() if isinstance(rows, list)),
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/codex-local-login":
        try:
            if not self.is_local_admin_request():
                self.send_json(404, {"ok": False, "error": "Not found."})
                return
            marker = clean(self.headers.get("X-Future-Codex-Local-Login", ""))
            if marker != "1":
                self.send_json(403, {"ok": False, "error": "Missing local Codex test marker."})
                return
            payload = self.read_json_body()
            username = normalize_username(payload.get("username", ""))
            if not username:
                self.send_json(400, {"ok": False, "error": "Vui lòng nhập tên tài khoản.", "reason": "missing_username"})
                return
            if not server_database_user_exists(username):
                self.send_json(404, {"ok": False, "error": "Tài khoản không tồn tại.", "reason": "nouser"})
                return
            # Added 2026-07-06: lets Codex inspect the local DOM as a real user without exposing a tunnel login bypass.
            session = create_auth_session(username)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            profile = read_user_profile(username)
            preferences = read_user_preferences(username)
            server_data = ensure_server_data_folders(username)
            self.send_json(
                200,
                {
                    "ok": True,
                    "username": username,
                    "is_admin": is_admin_user(username),
                    "profile": profile,
                    "preferences": preferences,
                    "needs_profile": bool(profile_missing(profile)),
                    "missing": profile_missing(profile),
                    "server_data": server_data,
                    "codex_local_login": True,
                    **session,
                },
            )
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/login":
        try:
            payload = self.read_json_body()
            username = normalize_username(payload.get("username", ""))
            password = str(payload.get("password", "") or "")
            if not username:
                self.send_json(400, {"ok": False, "error": "Vui lòng nhập tên tài khoản.", "reason": "missing_username"})
                return
            if not password:
                self.send_json(400, {"ok": False, "error": "Vui lòng nhập mật khẩu.", "reason": "missing_password"})
                return
            fail_status = login_failure_status(self.anti_robot_client_key(), username)
            if fail_status.get("locked"):
                self.send_json(429, {
                    "ok": False,
                    "error": "Dang nhap sai qua 5 lan. Vui long doi 5 phut roi thu lai.",
                    "reason": "login_locked",
                    "retry_after": fail_status.get("retry_after", LOGIN_FAILURE_LOCK_SECONDS),
                })
                return
            if server_database_is_test_user(username) and not self.is_local_admin_request():
                self.send_json(403, {"ok": False, "error": "Load-test accounts are local-only.", "reason": "load_test_local_only"})
                return
            ok, reason, profile = check_user_login(username, password)
            if not ok:
                if reason == "blocked":
                    self.send_json(403, {
                        "ok": False,
                        "error": "Tai khoan nay dang bi admin chan dang nhap.",
                        "reason": "login_blocked",
                    })
                    return
                fail_status = record_login_failure(self.anti_robot_client_key(), username)
                if fail_status.get("locked"):
                    self.send_json(429, {
                        "ok": False,
                        "error": "Dang nhap sai qua 5 lan. Vui long doi 5 phut roi thu lai.",
                        "reason": "login_locked",
                        "retry_after": fail_status.get("retry_after", LOGIN_FAILURE_LOCK_SECONDS),
                    })
                    return
                status = 404 if reason == "nouser" else 401
                message = (
                    "Tài khoản không tồn tại. Hãy kiểm tra lại tên đăng nhập."
                    if reason == "nouser"
                    else "Mật khẩu không đúng. Hãy nhập lại mật khẩu."
                )
                self.send_json(status, {"ok": False, "error": message, "reason": reason})
                return
            clear_login_failures(self.anti_robot_client_key(), username)
            session = create_auth_session(username)
            if server_database_is_test_user(username):
                self.send_json(200, {
                    "ok": True,
                    "username": username,
                    "is_admin": False,
                    "profile": profile,
                    "preferences": read_user_preferences(username),
                    "needs_profile": False,
                    "missing": [],
                    "server_data": {"load_test": True},
                    "leaderboard_rewards_claimed": {"claims": [], "items": [], "scheduled": False},
                    **session,
                })
                return
            chat_mark_online(username)
            mark_user_activity(username, {"status": "Logged in"})
            start_main_vocab_sync_user(username, force=False, reason="future-login")
            record_login_event(username, {
                "client": self.client_address[0] if self.client_address else "",
                "user_agent": self.headers.get("User-Agent", ""),
            })
            server_data = ensure_server_data_folders(username)
            leaderboard_rewards_claimed = {"claims": [], "items": [], "scheduled": "login-background"}
            schedule_login_reward_claim(username)
            missing = profile_missing(profile)
            preferences = read_user_preferences(username)
            self.send_json(
                200,
                {
                    "ok": True,
                    "username": username,
                    "is_admin": is_admin_user(username),
                    "profile": profile,
                    "preferences": preferences,
                    "needs_profile": bool(missing),
                    "missing": missing,
                    "server_data": server_data,
                    "leaderboard_rewards_claimed": leaderboard_rewards_claimed,
                    **session,
                },
            )
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/password-reset/request":
        try:
            payload = self.read_json_body()
            result = request_password_reset_code(payload, client_key=self.anti_robot_client_key())
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/password-reset/confirm":
        try:
            payload = self.read_json_body()
            result = confirm_password_reset_code(payload, client_key=self.anti_robot_client_key())
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/password-reset/admin":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server duoc duyet doi mat khau."})
            return
        try:
            payload = self.read_json_body()
            result = approve_password_reset_request(payload.get("username", ""), payload.get("action", "accept"))
            self.send_json(200, {"ok": True, **result, "password_resets": list_pending_password_resets(), "pending": list_pending_registrations()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/register":
        try:
            payload = self.read_json_body()
            result = submit_pending_registration(payload)
            self.send_json(
                202,
                {
                    "ok": True,
                    "pending": True,
                    "message": "Da gui dang ky. Cho may server chap nhan.",
                    **result,
                },
            )
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/password/change":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            current_password = str(payload.get("current_password", payload.get("currentPassword", "")) or "")
            new_password = str(payload.get("new_password", payload.get("newPassword", "")) or "")
            ok, reason, _profile = check_user_login(username, current_password)
            if not ok:
                self.send_json(401, {"ok": False, "error": "Mat khau hien tai khong dung.", "reason": reason})
                return
            ok, message = validate_register_password(new_password)
            if not ok:
                self.send_json(400, {"ok": False, "error": message})
                return
            set_user_password_hash(username, new_password)
            self.send_json(200, {"ok": True, "username": username, "changed": True})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/profile":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            profile = save_user_profile(username, payload)
            server_data = ensure_server_data_folders(username)
            preferences = read_user_preferences(username)
            self.send_json(200, {"ok": True, "username": username, "profile": profile, "preferences": preferences, "needs_profile": False, "server_data": server_data})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/preferences":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            preferences = save_user_preferences(username, payload)
            if clean(self.headers.get("X-Future-Response-Mode", "")).lower() == "preferences-compact-v1":
                self.send_json(200, {
                    "ok": True,
                    "username": username,
                    "server_revision": max(0, int(preferences.get("_serverRevision", 0) or 0)),
                    "updated_at": clean(preferences.get("updated_at", "")),
                })
            else:
                self.send_json(200, {"ok": True, "username": username, "preferences": preferences})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/server-data/last-file":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            state = remember_lesson_last_file(username, payload)
            self.send_json(200, {"ok": True, "username": username, "state": state})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/approve":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server duoc duyet dang ky."})
            return
        try:
            payload = self.read_json_body()
            result = approve_pending_registration(payload.get("username", ""), payload.get("action", "accept"))
            self.send_json(200, {"ok": True, **result, "pending": list_pending_registrations(), "password_resets": list_pending_password_resets()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/chat/upload":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            fields, files = parse_multipart_form(self.headers, self.rfile, max_bytes=34 * 1024 * 1024)
            upload = files.get("file") or files.get("attachment") or (next(iter(files.values())) if files else None)
            if not upload:
                raise RuntimeError("Chua chon tep dinh kem.")
            username = session.get("username", "")
            chat_mark_online(username)
            attachment = save_chat_attachment(username, upload, "user")
            text = str(fields.get("text", "") or "")
            audio_enabled = truthy(fields.get("audio_enabled", ""), False)
            language = clean(fields.get("language", "en")).lower()
            if language != "vi":
                language = "en"
            voice = clean(fields.get("voice", ""))
            label = clean(fields.get("voice_label", ""))
            extra = {"attachments": [attachment], "language": language}
            if text.strip() and audio_enabled and voice:
                try:
                    extra.update(chat_synthesize_message_audio_queued(text, voice, preferred_user=username))
                except Exception as exc:
                    # Added 2026-07-11: keep upload chat text when selected voice cannot synthesize.
                    extra["audio_error"] = clean(exc)
            item = chat_add_message(username, "user", text, extra=extra)
            self.send_json(200, {"ok": True, "message": item, "unread": chat_user_unread(username)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/chat/admin/upload":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi gui dinh kem chat."})
            return
        try:
            fields, files = parse_multipart_form(self.headers, self.rfile, max_bytes=34 * 1024 * 1024)
            username = fields.get("username", "")
            upload = files.get("file") or files.get("attachment") or (next(iter(files.values())) if files else None)
            if not upload:
                raise RuntimeError("Chua chon tep dinh kem.")
            attachment = save_chat_attachment(username, upload, "admin")
            text = str(fields.get("text", "") or "")
            audio_enabled = truthy(fields.get("audio_enabled", None), True)
            voice = clean(fields.get("voice", ""))
            extra = {"attachments": [attachment]}
            if text.strip() and audio_enabled and voice:
                try:
                    extra.update(chat_synthesize_message_audio_queued(text, voice, preferred_user=username))
                except Exception as exc:
                    # Added 2026-07-11: show voice synthesis failure in chat instead of dropping admin upload.
                    extra["audio_error"] = clean(exc)
            item = chat_add_message(username, "admin", text, extra=extra)
            self.send_json(200, {"ok": True, "message": item, **chat_admin_state(message_user=username)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/chat/send":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            text = str(payload.get("text", "") or "")
            audio_enabled = truthy(payload.get("audio_enabled", payload.get("audioEnabled")), False)
            language = clean(payload.get("language", "en")).lower()
            if language != "vi":
                language = "en"
            voice = clean(payload.get("voice", ""))
            label = clean(payload.get("voice_label", "") or payload.get("voiceLabel", ""))
            extra = {
                "language": language,
                "operation_id": clean(payload.get("operation_id") or payload.get("operationId") or "")[:160],
            }
            if text.strip() and audio_enabled and voice:
                try:
                    extra.update(chat_synthesize_message_audio_queued(text, voice, preferred_user=username))
                except Exception as exc:
                    # Added 2026-07-10: do not drop chat text when a cold/failed VI voice cannot synthesize.
                    extra["audio_error"] = clean(exc)
            item = chat_add_message(username, "user", text, extra=extra)
            self.send_json(200, {"ok": True, "message": item, "unread": chat_user_unread(username)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/chat/admin/send":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi gui chat."})
            return
        try:
            payload = self.read_json_body()
            text = str(payload.get("text", "") or "")
            voice = clean(payload.get("voice", ""))
            audio_enabled = truthy(payload.get("audio_enabled", payload.get("audioEnabled")), True)
            extra = {"operation_id": clean(payload.get("operation_id") or payload.get("operationId") or "")[:160]}
            if text.strip() and audio_enabled and voice:
                try:
                    extra.update(chat_synthesize_message_audio_queued(text, voice, preferred_user=payload.get("username", "")))
                except Exception as exc:
                    # Added 2026-07-11: keep admin chat visible when Kokoro VI voice is unavailable.
                    extra["audio_error"] = clean(exc)
            translated_from = clean(payload.get("translated_from", ""))
            if translated_from:
                extra["translated_from"] = translated_from
            item = chat_add_message(payload.get("username", ""), "admin", text, extra=extra)
            self.send_json(200, {"ok": True, "message": item, **chat_admin_state(message_user=payload.get("username", ""))})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/chat/admin/translate":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi dich chat."})
            return
        try:
            payload = self.read_json_body()
            source = str(payload.get("text", "") or "")
            translated = chat_translate_to_english(source)
            self.send_json(200, {"ok": True, "source": source, "translation": translated})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-w/speak-skip/request":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            request = request_space_w_speak_skip(username, payload)
            self.send_json(200, {"ok": True, "username": username, "request": request})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-w/speak-skip/respond":
        manager = self.speak_skip_admin_session()
        if not manager:
            self.send_json(403, {"ok": False, "error": "Chi admin moi duoc duyet Speak skip."})
            return
        try:
            payload = self.read_json_body()
            if payload.get("all") or clean(payload.get("id", payload.get("request_id", ""))).lower() in {"all", "*"}:
                requests = respond_space_w_speak_skip_many(payload.get("username", ""), payload.get("action", "accept"))
                self.send_json(200, {"ok": True, "requests": requests, "request": requests[0] if requests else None, **chat_admin_state()})
            else:
                request = respond_space_w_speak_skip(
                    payload.get("username", ""),
                    payload.get("id", payload.get("request_id", "")),
                    payload.get("action", "accept"),
                )
                self.send_json(200, {"ok": True, "request": request, **chat_admin_state()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/stream/request":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = session.get("username", "")
            chat_mark_online(username)
            self.send_json(200, {"ok": True, "session": stream_request(username, "user")})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/stream/action":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            self.send_json(200, {"ok": True, "session": stream_action(username, "user", payload.get("action", ""), payload.get("session", ""))})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/stream/chunk":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            self.send_json(200, {"ok": True, **stream_add_chunk(username, "user", payload.get("session", ""), payload.get("data", ""), payload.get("mime", ""))})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/stream/signal":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            result = stream_submit_signal(username, "user", payload.get("session", ""), payload.get("type", ""), payload.get("data", {}))
            self.send_json(200, {"ok": True, "session": result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/stream/admin/request":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi stream."})
            return
        try:
            payload = self.read_json_body()
            self.send_json(200, {"ok": True, "session": stream_request(payload.get("username", ""), "admin"), **chat_admin_state()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/stream/admin/signal":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi stream."})
            return
        try:
            payload = self.read_json_body()
            result = stream_submit_signal(payload.get("username", ""), "admin", payload.get("session", ""), payload.get("type", ""), payload.get("data", {}))
            self.send_json(200, {"ok": True, "session": result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/stream/admin/action":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi stream."})
            return
        try:
            payload = self.read_json_body()
            self.send_json(200, {"ok": True, "session": stream_action(payload.get("username", ""), "admin", payload.get("action", ""), payload.get("session", "")), **chat_admin_state()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/stream/admin/chunk":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi stream."})
            return
        try:
            payload = self.read_json_body()
            self.send_json(200, {"ok": True, **stream_add_chunk(payload.get("username", ""), "admin", payload.get("session", ""), payload.get("data", ""), payload.get("mime", ""))})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/action":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            self.send_json(200, {"ok": True, "session": screen_action(username, "user", payload.get("action", ""), payload.get("session", ""))})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/request":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = session.get("username", "")
            chat_mark_online(username)
            self.send_json(200, {"ok": True, "session": screen_request(username, "user")})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/frame":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            result = screen_store_frame(
                username,
                payload.get("session", ""),
                payload.get("data", ""),
                payload.get("width", 0),
                payload.get("height", 0),
            )
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/frame-binary":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            try:
                content_length = int(clean(self.headers.get("Content-Length", "0")) or 0)
            except ValueError:
                content_length = 0
            max_bytes = max(1, int((SCREEN_FRAME_MAX_CHARS - 64) * 3 / 4))
            if content_length <= 0:
                raise RuntimeError("Missing screen frame.")
            if content_length > max_bytes:
                raise RuntimeError("Screen frame qua lon.")
            raw = self.rfile.read(content_length)
            username = session.get("username", "")
            chat_mark_online(username)
            result = screen_store_frame_bytes(
                username,
                (query.get("session") or [""])[0],
                raw,
                (query.get("mime") or [self.headers.get("Content-Type", "image/webp")])[0],
                (query.get("width") or ["0"])[0],
                (query.get("height") or ["0"])[0],
            )
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/audio-chunk":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            result = screen_add_audio_chunk(
                username,
                payload.get("session", ""),
                payload.get("data", ""),
                payload.get("mime", ""),
                "user",
            )
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/auth-admin/audio-chunk":
        admin_session = self.auth_admin_session()
        if not admin_session:
            self.send_json(403, {"ok": False, "error": "Only admins can speak to screen users."})
            return
        try:
            payload = self.read_json_body()
            username = clean(payload.get("username", ""))
            chat_mark_online(admin_session.get("username", ""))
            result = screen_add_audio_chunk(
                username,
                payload.get("session", ""),
                payload.get("data", ""),
                payload.get("mime", ""),
                "admin",
            )
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/signal":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            result = screen_submit_signal(username, "user", payload.get("session", ""), payload.get("type", ""), payload.get("data", {}))
            self.send_json(200, {"ok": True, "session": result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/admin/request":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi yeu cau man hinh."})
            return
        try:
            payload = self.read_json_body()
            self.send_json(200, {"ok": True, "session": screen_request(payload.get("username", ""), "admin"), **chat_admin_state()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/auth-admin/request":
        admin_session = self.auth_admin_session()
        if not admin_session:
            self.send_json(403, {"ok": False, "error": "Only admins can request user screens."})
            return
        try:
            payload = self.read_json_body()
            chat_mark_online(admin_session.get("username", ""))
            self.send_json(200, {"ok": True, "session": screen_request(payload.get("username", ""), "admin"), **chat_admin_state()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/admin/signal":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi xem man hinh."})
            return
        try:
            payload = self.read_json_body()
            result = screen_submit_signal(payload.get("username", ""), "admin", payload.get("session", ""), payload.get("type", ""), payload.get("data", {}))
            self.send_json(200, {"ok": True, "session": result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/auth-admin/signal":
        admin_session = self.auth_admin_session()
        if not admin_session:
            self.send_json(403, {"ok": False, "error": "Only admins can send screen signals."})
            return
        try:
            payload = self.read_json_body()
            chat_mark_online(admin_session.get("username", ""))
            result = screen_submit_signal(payload.get("username", ""), "admin", payload.get("session", ""), payload.get("type", ""), payload.get("data", {}))
            self.send_json(200, {"ok": True, "session": result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/admin/control":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi dieu khien man hinh."})
            return
        try:
            payload = self.read_json_body()
            result = screen_add_control(
                payload.get("username", ""),
                payload.get("session", ""),
                payload.get("commands", payload.get("command", payload)),
            )
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/auth-admin/control":
        admin_session = self.auth_admin_session()
        if not admin_session:
            self.send_json(403, {"ok": False, "error": "Only admins can control user screens."})
            return
        try:
            payload = self.read_json_body()
            chat_mark_online(admin_session.get("username", ""))
            result = screen_add_control(
                payload.get("username", ""),
                payload.get("session", ""),
                payload.get("commands", payload.get("command", payload)),
            )
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/auth-admin/transport-log":
        admin_session = self.auth_admin_session()
        if not admin_session:
            self.send_json(403, {"ok": False, "error": "Only admins can write screen transport logs."})
            return
        try:
            payload = self.read_json_body()
            chat_mark_online(admin_session.get("username", ""))
            result = screen_transport_log_append(
                payload.get("username", ""),
                admin_session.get("username", ""),
                payload,
            )
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/admin/action":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi tat man hinh."})
            return
        try:
            payload = self.read_json_body()
            self.send_json(200, {"ok": True, "session": screen_action(payload.get("username", ""), "admin", payload.get("action", ""), payload.get("session", "")), **chat_admin_state()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/screen/auth-admin/action":
        admin_session = self.auth_admin_session()
        if not admin_session:
            self.send_json(403, {"ok": False, "error": "Only admins can stop user screens."})
            return
        try:
            payload = self.read_json_body()
            chat_mark_online(admin_session.get("username", ""))
            self.send_json(200, {"ok": True, "session": screen_action(payload.get("username", ""), "admin", payload.get("action", ""), payload.get("session", "")), **chat_admin_state()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/chat/admin/read":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi doc chat."})
            return
        try:
            payload = self.read_json_body()
            chat_mark_admin_read(payload.get("username", ""))
            self.send_json(200, {"ok": True, **chat_admin_state()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/chat/admin/clear":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi xoa chat."})
            return
        try:
            payload = self.read_json_body()
            result = clear_chat_for_user(payload.get("username", ""))
            self.send_json(200, {"ok": True, **result, **chat_admin_state()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/paint/sync":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            state = paint_update_state(username, payload.get("data", ""), payload.get("width", 0), payload.get("height", 0), "user")
            self.send_json(200, {"ok": True, "state": state})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/paint/cursor":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            state = paint_update_cursor(username, payload.get("cursor", payload), "user", username)
            self.send_json(200, {"ok": True, "state": state})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/paint/admin/sync":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi sua paint."})
            return
        try:
            payload = self.read_json_body()
            state = paint_update_state(payload.get("username", ""), payload.get("data", ""), payload.get("width", 0), payload.get("height", 0), "admin")
            self.send_json(200, {"ok": True, "state": state, **chat_admin_state()})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/paint/admin/cursor":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi sua paint."})
            return
        try:
            payload = self.read_json_body()
            state = paint_update_cursor(payload.get("username", ""), payload.get("cursor", payload), "admin", "Admin")
            self.send_json(200, {"ok": True, "state": state})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/announcements":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi duoc sua thong bao."})
            return
        try:
            payload = self.read_json_body()
            result = save_announcements(str(payload.get("text", "") or ""))
            self.send_json(200, {"ok": True, "raw": "\n".join(result.get("items", [])), **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/dashboard/space-v-picture-settings":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi dashboard tren may server moi duoc sua duong dan picture."})
            return
        try:
            payload = self.read_json_body()
            result = save_server_settings({"space_v_picture_folder": payload.get("folder", payload.get("path", ""))})
            picture = space_v_local_picture_settings_payload(force=True)
            self.send_json(200, {"ok": True, "updated_at": result.get("updated_at", ""), **picture})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/settings":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi duoc sua settings."})
            return
        try:
            payload = self.read_json_body()
            previous_settings = load_server_settings()
            result = save_server_settings(payload)
            enforce_all_chat_attachment_quotas()
            restart_tunnel_after_settings_change(previous_settings, result)
            self.send_json(200, {"ok": True, **public_server_settings(result)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/image-primary":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            word = lesson_task_notice_text(payload.get("word", ""), limit=180)
            image_id = lesson_task_notice_text(payload.get("image_id") or payload.get("imageId") or "", limit=260)
            if not word or not image_id:
                raise RuntimeError("Missing vocabulary image selection.")
            record = space_v_local_picture_asset(word, image_id=image_id)
            if not record or clean(record.get("image_id", "")).casefold() != image_id.casefold():
                raise RuntimeError("Vocabulary image no longer exists.")
            result = server_database_save_vocab_image_selection(
                session.get("username", ""),
                vocab_key(word),
                image_id,
                payload.get("operation_id") or payload.get("operationId") or "",
                payload.get("selected_epoch") or payload.get("selectedEpoch") or 0,
            )
            self.send_json(200, {"ok": True, "word": word, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/scan-space-w":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(urlparse(self.path).query)
            compact_response = clean((query.get("response") or [""])[0]).lower() == "compact-v1"
            payload = self.read_json_body()
            result = scan_space_w_vocabulary(payload.get("path", ""), session.get("username", ""), include_words=not compact_response, lesson_id=payload.get("lesson_id") or payload.get("lessonId") or "")
            self.send_json(200, {
                "ok": True,
                "response_schema": "vocab-scan-compact-v1" if compact_response else "vocab-scan-full-v1",
                **result,
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/build-mission":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            if bool(payload.get("async")) or bool(payload.get("background")):
                result = start_space_w_vocab_build_job(payload.get("path", ""), session.get("username", ""))
                self.send_json(202, {"ok": True, **result})
                return
            result = build_space_w_vocab_mission(payload.get("path", ""), session.get("username", ""))
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-w/progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(urlparse(self.path).query)
            compact_response = clean((query.get("response") or [""])[0]).lower() == "compact-v1"
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            if clean(payload.get("action")).lower() == "clear":
                result = clear_space_w_progress(username, payload)
                mark_user_activity(username, {"status": "Cleared Space_W progress", "space": "Space_W", "path": payload.get("path", "")})
                self.send_json(200, {"ok": True, "username": username, **result})
                return
            progress = save_space_w_progress(username, payload)
            completion_sync = progress.pop("_completionSync", None) if isinstance(progress, dict) else None
            completion_result = {}
            completion_error = ""
            if isinstance(completion_sync, dict) and clean(completion_sync.get("path", "")):
                try:
                    completion_result = record_lesson_completion(
                        completion_sync.get("path", ""),
                        username,
                        completion_sync,
                    )
                except Exception as completion_exc:
                    completion_error = str(completion_exc)
                    stt_debug_log(
                        "space_w_progress_completion_sync_failed",
                        user=username,
                        path=completion_sync.get("path", ""),
                        error=completion_error,
                    )
            mark_user_activity(username, {
                "status": "Completed lesson" if completion_result else "Studying Space_W",
                "space": "Space_W",
                "title": progress.get("title", ""),
                "path": progress.get("path", ""),
                "nodeIndex": progress.get("nodeIndex", 0),
                "nodeCount": progress.get("nodeCount", 0),
            })
            payload_state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
            request_operation_id = clean(payload.get("syncOperationId") or payload.get("sync_operation_id") or payload_state.get("syncOperationId"))
            progress_operation_id = clean(progress.get("syncOperationId") or progress.get("sync_operation_id"))
            use_compact = bool(compact_response and request_operation_id and request_operation_id == progress_operation_id)
            self.send_json(200, {
                "ok": True,
                "username": username,
                "progress": space_w_progress_compact_response(progress) if use_compact else progress,
                "response_schema": "space-w-progress-compact-v1" if use_compact else "space-w-progress-full-v1",
                "completion": completion_result,
                "completion_pending": bool(completion_error),
                "completion_error": completion_error,
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-q/progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(urlparse(self.path).query)
            compact_response = clean((query.get("response") or [""])[0]).lower() == "compact-v1"
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            if clean(payload.get("action")).lower() == "clear":
                started = time.perf_counter()
                result = clear_space_q_progress(username, payload)
                mark_user_activity(username, {"status": "Cleared Space_Q progress", "space": "Space_Q", "path": payload.get("path", "")})
                self.send_json(200, {"ok": True, "username": username, "progress_save_ms": int((time.perf_counter() - started) * 1000), **result})
                return
            started = time.perf_counter()
            progress = save_space_q_progress(username, payload)
            mark_user_activity(username, {
                "status": "Studying Space_Q",
                "space": "Space_Q",
                "title": progress.get("title", ""),
                "path": progress.get("path", ""),
                "nodeIndex": progress.get("nodeIndex", 0),
                "nodeCount": progress.get("nodeCount", 0),
            })
            payload_state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
            request_operation_id = clean(payload.get("syncOperationId") or payload.get("sync_operation_id") or payload_state.get("syncOperationId"))
            progress_operation_id = clean(progress.get("syncOperationId") or progress.get("sync_operation_id"))
            use_compact = bool(compact_response and request_operation_id and request_operation_id == progress_operation_id)
            self.send_json(200, {
                "ok": True,
                "username": username,
                "progress": space_w_progress_compact_response(progress) if use_compact else progress,
                "progress_save_ms": int((time.perf_counter() - started) * 1000),
                "response_schema": "space-q-progress-compact-v1" if use_compact else "space-q-progress-full-v1",
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-v/progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(urlparse(self.path).query)
            compact_response = clean((query.get("response") or [""])[0]).lower() == "compact-v1"
            payload = self.read_json_body()
            if not getattr(self, "_future_completion_trace", None) and clean(payload.get("completion_trace_id") or ""):
                self.completion_trace_begin(path, clean(payload.get("completion_trace_id") or ""))
            username = session.get("username", "")
            chat_mark_online(username)
            action = clean(payload.get("action", "")).lower()
            if action == "clear":
                result = clear_space_v_progress(username, payload)
                self.send_json(200, {"ok": True, "username": username, **result})
                return
            progress = save_space_v_progress(username, payload)
            registry_sync = {}
            if space_v_registry_sync_has_completion_marker(progress):
                registry_sync = start_space_v_registry_sync_job(
                    username,
                    progress,
                    reason=clean(action) or "space-v-progress-complete",
                    delay_seconds=0.05,
                )
            mark_user_activity(username, {
                "status": "Studying Space_V",
                "space": "Space_V",
                "title": progress.get("title", ""),
                "path": progress.get("path", ""),
                "nodeIndex": progress.get("nodeIndex", 0),
                "nodeCount": progress.get("nodeCount", 0),
            })
            self.send_json(200, {
                "ok": True,
                "username": username,
                "progress": space_v_progress_compact_response(progress) if compact_response else progress,
                "response_schema": "space-v-progress-compact-v1" if compact_response else "space-v-progress-full-v1",
                "summary": space_v_progress_summary_from_record(progress),
                "registry_sync": registry_sync,
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-p/progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(urlparse(self.path).query)
            compact_response = clean((query.get("response") or [""])[0]).lower() == "compact-v1"
            payload = self.read_json_body()
            username = session.get("username", "")
            chat_mark_online(username)
            if clean(payload.get("action")).lower() == "clear":
                clear_state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
                clear_space = normalize_paragraph_progress_space(payload.get("space") or clear_state.get("spaceMode"))
                result = clear_space_p_progress(username, payload)
                mark_user_activity(username, {"status": f"Cleared {clear_space} progress", "space": clear_space, "path": payload.get("path", "")})
                self.send_json(200, {"ok": True, "username": username, **result})
                return
            progress = save_space_p_progress(username, payload)
            payload_state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
            progress_space = normalize_paragraph_progress_space(progress.get("space") or payload.get("space") or payload_state.get("spaceMode"))
            mark_user_activity(username, {
                "status": f"Studying {progress_space}",
                "space": progress_space,
                "title": progress.get("title", ""),
                "path": progress.get("path", ""),
                "nodeIndex": progress.get("nodeIndex", 0),
                "nodeCount": progress.get("nodeCount", 0),
            })
            request_operation_id = clean(payload.get("syncOperationId") or payload.get("sync_operation_id") or payload_state.get("syncOperationId"))
            progress_operation_id = clean(progress.get("syncOperationId") or progress.get("sync_operation_id"))
            use_compact = bool(compact_response and request_operation_id and request_operation_id == progress_operation_id)
            self.send_json(200, {
                "ok": True,
                "username": username,
                "progress": space_p_progress_compact_response(progress) if use_compact else progress,
                "response_schema": "space-p-progress-compact-v1" if use_compact else "space-p-progress-full-v1",
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body() or {}
            viewer = normalize_username(session.get("username", ""))
            target_user = normalize_username(payload.get("user", "") or payload.get("target_user", "") or viewer)
            admin_view = target_user != viewer
            query = parse_qs(urlparse(self.path).query)
            client_source = clean((query.get("client_source") or [""])[0]).lower()
            pin_only = bool(payload.get("pinOnly") or client_source == "pdf_pin_save")
            SERVER_STATE["last_space_pdf_progress_post"] = {
                "at": utc_timestamp(),
                "viewer": viewer,
                "target_user": target_user,
                "source": client_source,
                "pin_only": pin_only,
                "received_pins": payload.get("pinnedPages", []),
                "ok": False,
            }
            if admin_view and not is_admin_user(viewer):
                self.send_json(403, {"ok": False, "error": "Only admins can update another user's Space_PDF progress."})
                return
            if not pin_only:
                chat_mark_online(viewer)
            if clean(payload.get("action")).lower() == "clear":
                result = clear_space_pdf_progress(target_user, payload)
                mark_user_activity(viewer, {
                    "status": "Cleared Space_PDF progress" if not admin_view else f"Cleared Space_PDF progress as @{target_user}",
                    "space": "Space_PDF",
                    "path": payload.get("path", ""),
                })
                self.send_json(200, {"ok": True, "username": target_user, "viewer": viewer, "admin_view": admin_view, **result})
                return
            progress = save_space_pdf_progress(target_user, payload)
            SERVER_STATE["last_space_pdf_progress_post"] = {
                **SERVER_STATE.get("last_space_pdf_progress_post", {}),
                "ok": True,
                "saved_pins": progress.get("pinnedPages", []),
                "saved_pin_at": progress.get("pinnedPagesUpdatedAt", ""),
            }
            if not pin_only:
                mark_user_activity(viewer, {
                    "status": "Studying Space_PDF" if not admin_view else f"Studying Space_PDF as @{target_user}",
                    "space": "Space_PDF",
                    "title": progress.get("title", ""),
                    "path": progress.get("path", ""),
                    "page": progress.get("page", 1),
                    "pages": progress.get("pages", 0),
                })
            self.send_json(200, {"ok": True, "username": target_user, "viewer": viewer, "admin_view": admin_view, "progress": progress})
        except PermissionError as exc:
            SERVER_STATE["last_space_pdf_progress_post"] = {
                **SERVER_STATE.get("last_space_pdf_progress_post", {}),
                "at": utc_timestamp(),
                "ok": False,
                "error": str(exc),
            }
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            SERVER_STATE["last_space_pdf_progress_post"] = {
                **SERVER_STATE.get("last_space_pdf_progress_post", {}),
                "at": utc_timestamp(),
                "ok": False,
                "error": str(exc),
            }
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/drawing":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body() or {}
            viewer = normalize_username(session.get("username", ""))
            target_user = normalize_username(payload.get("user", "") or payload.get("target_user", "") or viewer)
            admin_view = target_user != viewer
            if admin_view and not is_admin_user(viewer):
                self.send_json(403, {"ok": False, "error": "Only admins can update another user's PDF drawing."})
                return
            drawing = save_space_pdf_drawing(target_user, payload, updated_by=viewer)
            # Added 2026-07-20: drawing autosaves are durable state deltas, not user-activity events.
            self.send_json(200, {"ok": True, "username": target_user, "viewer": viewer, "admin_view": admin_view, "drawing": drawing})
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/audio-markers":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            viewer = normalize_username(session.get("username", ""))
            if not is_admin_user(viewer):
                self.send_json(403, {"ok": False, "error": "Only admins can update shared PDF/Picture audio markers."})
                return
            payload = self.read_json_body() or {}
            chat_mark_online(viewer)
            result = save_space_pdf_shared_audio_marker(viewer, payload)
            mark_user_activity(viewer, {
                "status": "Updating shared PDF audio marker",
                "space": "Space_PDF",
                "path": payload.get("path", ""),
                "page": payload.get("page", 1),
            })
            self.send_json(200, {"ok": True, "viewer": viewer, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/ai-region-notices":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            viewer = normalize_username(session.get("username", ""))
            payload = self.read_json_body() or {}
            action = clean(payload.get("action", "save")).lower()
            if action == "ensure_audio":
                result = ensure_space_pdf_ai_region_notice_audio(viewer, payload)
                self.send_json(200, {"ok": True, "viewer": viewer, **result})
                return
            if not is_admin_user(viewer):
                self.send_json(403, {"ok": False, "error": "Only admins can update shared PDF/Picture AI notices."})
                return
            chat_mark_online(viewer)
            result = save_space_pdf_ai_region_notice(viewer, payload)
            mark_user_activity(viewer, {
                "status": "Updating shared PDF AI notice",
                "space": "Space_PDF",
                "path": payload.get("path", ""),
                "page": payload.get("page", 1),
            })
            self.send_json(200, {"ok": True, "viewer": viewer, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/ai-region-questions":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            viewer = normalize_username(session.get("username", ""))
            if not is_admin_user(viewer):
                self.send_json(403, {"ok": False, "error": "Only admins can update shared PDF/Picture AI questions."})
                return
            payload = self.read_json_body() or {}
            chat_mark_online(viewer)
            result = save_space_pdf_ai_region_question(viewer, payload)
            mark_user_activity(viewer, {
                "status": "Updating shared PDF AI question",
                "space": "Space_PDF",
                "path": payload.get("path", ""),
                "page": payload.get("page", 1),
            })
            self.send_json(200, {"ok": True, "viewer": viewer, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/ai-question-progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            viewer = normalize_username(session.get("username", ""))
            payload = self.read_json_body() or {}
            chat_mark_online(viewer)
            result = save_space_pdf_ai_question_progress(viewer, payload)
            mark_user_activity(viewer, {
                "status": "Saving MishiKa question progress",
                "space": "Space_PDF",
                "path": payload.get("path", ""),
                "page": payload.get("page", 1),
            })
            self.send_json(200, {"ok": True, "viewer": viewer, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/audio-marker-server-file":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            viewer = normalize_username(session.get("username", ""))
            if not is_admin_user(viewer):
                self.send_json(403, {"ok": False, "error": "Only admins can upload shared PDF/Picture audio markers."})
                return
            payload = self.read_json_body() or {}
            chat_mark_online(viewer)
            result = save_space_pdf_shared_audio_server_file(viewer, payload)
            mark_user_activity(viewer, {
                "status": "Loading shared PDF audio marker from server",
                "space": "Space_PDF",
                "path": payload.get("path", ""),
                "page": payload.get("page", 1),
            })
            self.send_json(200, {"ok": True, "viewer": viewer, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/audio-marker-server-pick":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            viewer = normalize_username(session.get("username", ""))
            if not is_admin_user(viewer):
                self.send_json(403, {"ok": False, "error": "Only admins can upload shared PDF/Picture audio markers."})
                return
            payload = self.read_json_body() or {}
            chat_mark_online(viewer)
            result = pick_space_pdf_shared_audio_server_file(viewer, payload)
            mark_user_activity(viewer, {
                "status": "Picking shared PDF audio marker on server",
                "space": "Space_PDF",
                "path": payload.get("path", ""),
                "page": payload.get("page", 1),
            })
            self.send_json(200, {"ok": True, "viewer": viewer, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/audio-marker-upload":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            viewer = normalize_username(session.get("username", ""))
            if not is_admin_user(viewer):
                self.send_json(403, {"ok": False, "error": "Only admins can upload shared PDF/Picture audio markers."})
                return
            fields, files = parse_multipart_form(self.headers, self.rfile, max_bytes=52 * 1024 * 1024)
            upload = files.get("file") or files.get("audio")
            if not upload:
                self.send_json(400, {"ok": False, "error": "No audio file selected."})
                return
            chat_mark_online(viewer)
            result = save_space_pdf_shared_audio_upload(viewer, upload, fields)
            mark_user_activity(viewer, {
                "status": "Uploading shared PDF audio marker",
                "space": "Space_PDF",
                "path": fields.get("path", ""),
                "page": fields.get("page", 1),
            })
            self.send_json(200, {"ok": True, "viewer": viewer, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/file-key-map":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            viewer = normalize_username(session.get("username", ""))
            admin_view = is_admin_user(viewer)
            target_user = normalize_username(payload.get("user", "") or viewer)
            if target_user != viewer and not admin_view:
                self.send_json(403, {"ok": False, "error": "Only admins can inspect another user's vocabulary stats."})
                return
            raw_candidates = [
                payload.get("path", ""),
                payload.get("effective_path", ""),
                payload.get("link_target", ""),
                payload.get("linked_path", ""),
                *(payload.get("aliases") if isinstance(payload.get("aliases"), list) else []),
            ]
            candidates = []
            seen_paths = set()
            for raw_candidate in raw_candidates:
                candidate = clean_path_value(raw_candidate)
                if candidate and candidate.lower() not in seen_paths:
                    seen_paths.add(candidate.lower())
                    candidates.append(candidate)
            if not candidates:
                raise RuntimeError("Thieu duong dan file lesson.")
            result = None
            last_error = None
            for candidate in candidates:
                try:
                    display_target = safe_server_data_path(candidate, viewer, admin=admin_view)
                    effective_target = server_data_effective_file_path(display_target, viewer, admin=admin_view)
                    meta = lesson_file_vocab_meta_for_target(effective_target)
                    word_keys = list(meta.get("vocab_word_keys") or []) if isinstance(meta, dict) else []
                    if not word_keys:
                        continue
                    result = {
                        "path": candidate,
                        "resolved_path": server_data_relative(effective_target),
                        "lesson_id": clean(payload.get("lesson_id", ""))[:240],
                        "vocab_word_keys": word_keys,
                        "vocab_total_words": max(0, int(meta.get("vocab_total_words", len(word_keys)) or len(word_keys))),
                        "vocab_space": clean(meta.get("vocab_space", "Lesson")),
                    }
                    stats = server_database_vocab_file_key_stats(
                        target_user,
                        word_keys,
                        {scope: vocab_period_bucket(scope) for scope in ("day", "week", "month")},
                        server_database_load_period_resets(),
                    )
                    result["vocab_stats"] = {**stats, "user": target_user, "path": candidate, "space": result["vocab_space"], "localEstimate": False, "cachedAt": utc_timestamp()}
                    break
                except Exception as key_exc:
                    last_error = key_exc
            if result is None:
                raise RuntimeError(str(last_error) if last_error else "Khong co vocabulary metadata cho file.")
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/file-stats":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            viewer = normalize_username(session.get("username", ""))
            target_user = normalize_username(payload.get("user", "") or viewer)
            if target_user != viewer and not is_admin_user(viewer):
                self.send_json(403, {"ok": False, "error": "Only admins can inspect another user's vocabulary stats."})
                return
            raw_candidates = [
                payload.get("path", ""),
                payload.get("effective_path", ""),
                payload.get("link_target", ""),
                payload.get("linked_path", ""),
            ]
            raw_aliases = payload.get("aliases") if isinstance(payload.get("aliases"), list) else []
            raw_candidates.extend(raw_aliases)
            candidates = []
            seen_paths = set()
            for raw_candidate in raw_candidates:
                candidate = clean_path_value(raw_candidate)
                if candidate and candidate.lower() not in seen_paths:
                    seen_paths.add(candidate.lower())
                    candidates.append(candidate)
            if not candidates:
                raise RuntimeError("Thieu duong dan file lesson.")
            last_error = None
            result = None
            for candidate in candidates:
                try:
                    result = space_v_file_vocabulary_stats(candidate, viewer, target_user)
                    result["resolved_path"] = result.get("path") or candidate
                    result["requested_path"] = clean_path_value(payload.get("path", ""))
                    break
                except Exception as stats_exc:
                    last_error = stats_exc
            if result is None:
                raise RuntimeError(str(last_error) if last_error else "Khong doc duoc thong ke tu vung.")
            chat_mark_online(viewer)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/lesson-index":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            viewer = normalize_username(session.get("username", ""))
            result = vocab_lesson_index_for_user(viewer)
            chat_mark_online(viewer)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/leaderboard/reset":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi duoc reset top."})
            return
        try:
            payload = self.read_json_body()
            raw_scopes = payload.get("scopes") if isinstance(payload.get("scopes"), list) else [payload.get("scope", "")]
            result = reset_vocab_leaderboard_periods(raw_scopes)
            self.send_json(200, {"ok": True, **result, **vocabulary_leaderboard(10, double_check=True)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-leaderboard/reset-today-test":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi duoc reset Space lesson Top Today."})
            return
        try:
            payload = self.read_json_body()
            raw_types = payload.get("board_types") if isinstance(payload.get("board_types"), list) else []
            result = reset_space_leaderboard_today_credit_for_testing(raw_types)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/leaderboard/npc-top/buff":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            admin_username = normalize_username(session.get("username", ""))
            if not is_admin_user(admin_username):
                self.send_json(403, {"ok": False, "error": "Only admins can buff NPC racers."})
                return
            payload = self.read_json_body()
            result = buff_vocab_leaderboard_npc_top(
                payload.get("username", payload.get("user", "")),
                space_w_int(payload.get("amount", payload.get("count", 0)), 0),
                admin_username=admin_username,
            )
            self.send_json(200, {"ok": True, "buff": result, "npcs": npc_top_public_roster(), **vocabulary_leaderboard(10, double_check=False, viewer=admin_username)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/leaderboard/status":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            result = set_vocab_leaderboard_status(username, payload.get("scope", "total"), payload.get("status", ""))
            self.send_json(200 if result.get("ok") else 400, result)
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/leaderboard/react":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            actor = normalize_username(session.get("username", ""))
            result = toggle_vocab_leaderboard_reaction(
                actor,
                payload.get("target", ""),
                payload.get("scope", "total"),
                payload.get("reaction", "like"),
            )
            self.send_json(200 if result.get("ok") else 400, result)
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/leaderboard/chat":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            actor = resolve_admin_npc_actor(username, payload.get("actor", payload.get("as", "")) if isinstance(payload, dict) else "")
            operation_id = payload.get("world_chat_operation_id", payload.get("operation_id", "")) if isinstance(payload, dict) else ""
            result = add_vocab_leaderboard_chat_message(actor, payload.get("message", ""), operation_id)
            chat_mark_online(username)
            self.send_json(200 if result.get("ok") else 400, result)
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/move":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            actor = resolve_admin_npc_actor(username, payload.get("actor", payload.get("as", "")) if isinstance(payload, dict) else "")
            result = shared_world_move(actor, payload, real_username=username)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if actor != username:
                result["world"]["real_user"] = username
                result["world"]["acting_as"] = actor
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/keyboard-pass":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            result = buy_shared_world_keyboard_pass(username)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            self.send_json(200, {"ok": True, "username": username, "is_admin": is_admin_user(username), **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/chat":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            actor = resolve_admin_npc_actor(username, payload.get("actor", payload.get("as", "")) if isinstance(payload, dict) else "")
            result = shared_world_chat(actor, payload, real_username=username)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if actor != username:
                result["world"]["real_user"] = username
                result["world"]["acting_as"] = actor
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/action":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            actor = resolve_admin_npc_actor(username, payload.get("actor", payload.get("as", "")) if isinstance(payload, dict) else "")
            result = shared_world_action(actor, payload, real_username=username)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if actor != username:
                result["world"]["real_user"] = username
                result["world"]["acting_as"] = actor
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/training/select":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            result = qm_city_training_select(username, payload)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/training/answer":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            result = qm_city_training_answer(username, payload)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/training/upgrade":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            result = qm_city_training_upgrade(username, payload)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/training/skill":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            result = qm_city_training_cast_skill(username, payload)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/training/reset":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            result = qm_city_training_reset(username)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/battle/invite":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            actor = resolve_admin_npc_actor(username, payload.get("actor", payload.get("as", "")) if isinstance(payload, dict) else "")
            result = shared_world_battle_invite(actor, payload)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if actor != username:
                result["real_user"] = username
                result["acting_as"] = actor
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            try:
                payload = locals().get("payload", {})
                stt_debug_log(
                    "picture_ocr_failed",
                    username=locals().get("username", ""),
                    path=locals().get("rel_path", ""),
                    page=(payload.get("page", 1) if isinstance(payload, dict) else 1),
                    rect=(payload.get("rect", {}) if isinstance(payload, dict) else {}),
                    error=str(exc),
                )
            except Exception:
                pass
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/battle/respond":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            actor = resolve_admin_npc_actor(username, payload.get("actor", payload.get("as", "")) if isinstance(payload, dict) else "")
            result = shared_world_battle_respond(actor, payload)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if actor != username:
                result["real_user"] = username
                result["acting_as"] = actor
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/battle/answer":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            actor = resolve_admin_npc_actor(username, payload.get("actor", payload.get("as", "")) if isinstance(payload, dict) else "")
            result = shared_world_battle_answer(actor, payload)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if actor != username:
                result["real_user"] = username
                result["acting_as"] = actor
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/battle/skill":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            actor = resolve_admin_npc_actor(username, payload.get("actor", payload.get("as", "")) if isinstance(payload, dict) else "")
            result = shared_world_battle_skill(actor, payload)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if actor != username:
                result["real_user"] = username
                result["acting_as"] = actor
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/battle/forfeit":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = normalize_username(session.get("username", ""))
            actor = resolve_admin_npc_actor(username, payload.get("actor", payload.get("as", "")) if isinstance(payload, dict) else "")
            result = shared_world_battle_forfeit(actor, payload)
            chat_mark_online(username)
            touch_user_activity_seen(username)
            if actor != username:
                result["real_user"] = username
                result["acting_as"] = actor
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/registry/sync":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            raw_words = payload.get("words") if isinstance(payload.get("words"), list) else (
                payload.get("learnedWords") if isinstance(payload.get("learnedWords"), list) else []
            )
            allowed, ignore_reason = space_v_registry_sync_allowed(username, payload)
            if not allowed:
                chat_mark_online(username)
                summary = read_user_vocab_registry_summary(username)
                self.send_json(200, {
                    "ok": True,
                    "username": username,
                    "ignored": True,
                    "reason": ignore_reason,
                    "total_words": max(0, space_w_int(summary.get("total_words", 0), 0)),
                    "updated_at": clean(summary.get("updated_at", "")),
                    "response_schema": "vocab-registry-sync-compact-v1",
                })
                return
            result = record_user_vocabulary_items(
                username,
                raw_words,
                clean(payload.get("path", "")),
                increment_count=False,
                sync_main=False,
                verify_registry=False,
            )
            chat_mark_online(username)
            mark_user_activity(username, {
                "status": "Syncing Space_V vocabulary",
                "space": "Space_V",
                "title": clean(payload.get("title", "")),
                "path": clean(payload.get("path", "")),
                "nodeIndex": 0,
                "nodeCount": max(0, space_w_int(result.get("total_words", 0), 0)),
            })
            summary = read_user_vocab_registry_summary(username)
            self.send_json(200, {
                "ok": True,
                "username": username,
                "vocabulary": result,
                "total_words": max(0, space_w_int(summary.get("total_words", result.get("total_words", 0)), 0)),
                "updated_at": clean(summary.get("updated_at", "")),
                "response_schema": "vocab-registry-sync-compact-v1",
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/sync-main-offline-push":
        try:
            payload = self.read_json_body()
            reason = clean(payload.get("reason", "")) or "main-login-remote"
            result = start_pushed_main_vocab_sync(payload, reason=reason)
            self.send_json(202, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/inventory/award":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(urlparse(self.path).query)
            delta_response = clean((query.get("response") or [""])[0]).lower() == "delta-v1"
            payload = self.read_json_body()
            result = award_inventory_item(session.get("username", ""), payload)
            if not delta_response:
                result["inventory"] = public_inventory(session.get("username", "")).get("inventory", {})
                result["inventory_delta"] = False
            result["response_schema"] = "inventory-delta-v1" if delta_response else "inventory-full-v1"
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/game/create":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            room = game_create_room(session.get("username", ""), payload)
            self.send_json(200, {"ok": True, "room": room})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/game/join":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            room = game_join_room(session.get("username", ""), payload.get("room", ""))
            self.send_json(200, {"ok": True, "room": room})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/game/select":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            room = game_select_words(session.get("username", ""), payload)
            self.send_json(200, {"ok": True, "room": room})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/game/ready":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            room = game_ready(session.get("username", ""), payload)
            self.send_json(200, {"ok": True, "room": room})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/game/cancel":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            result = game_cancel_room(session.get("username", ""), payload)
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/lessons/open":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body() or {}
            username = normalize_username(session.get("username", ""))
            descriptor = open_lesson_descriptor(
                username,
                payload.get("path", ""),
                admin=is_admin_user(username),
            )
            self.send_json(200, {"ok": True, "username": username, "lesson": descriptor})
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/lesson/time":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            username = session.get("username", "")
            rate_allowed, retry_after = anti_robot_rate_allowed(f"lesson-time:{normalize_username(username).lower()}", 12, 10)
            if not rate_allowed:
                self.send_json(429, {"ok": False, "error": "Lesson heartbeat rate limit exceeded.", "retryAfter": retry_after})
                return
            row = add_lesson_study_time(username, payload)
            if max(0, space_w_int(row.get("acceptedSeconds", 0), 0)) > 0 or clean(row.get("heartbeatReason", "")) == "session_started":
                chat_mark_online(username)
                mark_user_activity(username, {
                    "status": "Studying lesson",
                    "space": clean(row.get("space", "")),
                    "title": clean(row.get("title", "")),
                    "path": clean(row.get("path", "")),
                    "studySeconds": int(row.get("seconds", 0) or 0),
                })
            self.send_json(200, {"ok": True, "username": username, "time": row})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/lesson/complete":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            payload = self.read_json_body()
            trace_id = clean(payload.get("completion_trace_id") or self.headers.get("X-Future-Completion-Trace", ""))[:160]
            completion_transaction_prepare = globals().get("postgres_request_transaction_prepare")
            completion_transaction_commit = globals().get("postgres_request_transaction_commit")
            completion_transaction_rollback = globals().get("postgres_request_transaction_rollback")
            if callable(completion_transaction_prepare):
                completion_transaction_prepare()
            result = record_lesson_completion(
                payload.get("path", ""),
                session.get("username", ""),
                payload,
            )
            if callable(completion_transaction_commit):
                completion_transaction_commit()
            if trace_id and isinstance(result, dict):
                result["completion_trace_id"] = trace_id
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            if callable(locals().get("completion_transaction_rollback")):
                try:
                    completion_transaction_rollback()
                except Exception:
                    pass
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/transcribe-zipformer-vi":
        try:
            stt_debug_log(
                "zipformer_vi_request_begin",
                client=self.client_address[0] if self.client_address else "",
                content_type=clean(self.headers.get("Content-Type", "")),
                content_length=clean(self.headers.get("Content-Length", "")),
            )
            fields, files = parse_multipart_form(self.headers, self.rfile)
            stt_debug_log("zipformer_vi_request_multipart_parsed", fields=list(fields.keys()), files=list(files.keys()))
            audio_item = files.get("audio")
            if not audio_item or not audio_item.get("data"):
                stt_debug_log("zipformer_vi_request_missing_audio")
                self.send_json(400, {"ok": False, "error": "Missing audio field."})
                return
            suffix = Path(clean(audio_item.get("filename", "recording.wav"))).suffix or ".wav"
            audio_dir = Path(tempfile.gettempdir()) / "future_zipformer_vi_recordings"
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_path = audio_dir / f"future_zipformer_vi_{int(time.time())}_{uuid.uuid4().hex}{suffix}"
            with audio_path.open("wb") as fh:
                fh.write(audio_item["data"])
            stt_debug_log(
                "zipformer_vi_request_audio_saved",
                audio_path=str(audio_path),
                audio_size=audio_path.stat().st_size if audio_path.is_file() else 0,
                upload_filename=clean(audio_item.get("filename", "")),
                upload_content_type=clean(audio_item.get("content_type", "")),
                source=clean(fields.get("source", "")),
            )
            result = transcribe_zipformer_vi_audio(str(audio_path))
            job_id = uuid.uuid4().hex[:12]
            self.send_json(
                200,
                {
                    "ok": True,
                    "audio_path": str(audio_path),
                    "job_id": job_id,
                    "queue_position": 1,
                    "queue_wait_ms": 0,
                    "queue_process_ms": result.get("elapsed_ms", 0),
                    **result,
                },
            )
        except Exception as exc:
            SERVER_STATE.update({"loading": False, "zipformer_vi_last_error": str(exc), "last_error": str(exc)})
            stt_debug_log("zipformer_vi_request_exception", error=str(exc), traceback=traceback.format_exc())
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path != "/transcribe":
        self.send_json(404, {"ok": False, "error": "Not found"})
        return
    try:
        stt_debug_log(
            "request_begin",
            client=self.client_address[0] if self.client_address else "",
            content_type=clean(self.headers.get("Content-Type", "")),
            content_length=clean(self.headers.get("Content-Length", "")),
        )
        fields, files = parse_multipart_form(self.headers, self.rfile)
        stt_debug_log("request_multipart_parsed", fields=list(fields.keys()), files=list(files.keys()))
        session = self.auth_session()
        preferred_user = clean((session or {}).get("username", "") or fields.get("username", "") or fields.get("user", ""))
        audio_item = files.get("audio")
        if not audio_item or not audio_item.get("data"):
            stt_debug_log("request_missing_audio")
            self.send_json(400, {"ok": False, "error": "Missing audio field."})
            return
        request_source = clean(fields.get("source", fields.get("space", ""))).lower().replace("-", "_")
        upload_filename = clean(audio_item.get("filename", "")).lower()
        is_space_w_request = (
            request_source in {"space_w", "spacew", "space_w_speak", "future_space_w"}
            or upload_filename.startswith("future-speaking")
            or truthy(fields.get("space_w", fields.get("spaceW", "")), False)
        )
        is_ghost_eye_speak_request = (
            request_source in {"ghost_eye_speak", "ghost_eye", "pdf_speak", "pdf_speak_training"}
            or upload_filename.startswith("ghost-eye-speaking")
        )
        if (is_space_w_request or is_ghost_eye_speak_request) and not bool(load_server_settings().get("space_w_ai_check_voice_enabled", DEFAULT_SETTINGS["space_w_ai_check_voice_enabled"])):
            stt_debug_log("request_server_whisper_disabled", source=request_source, filename=upload_filename)
            disabled_code = "ghost_eye_whisper_disabled" if is_ghost_eye_speak_request else "space_w_whisper_disabled"
            disabled_label = "Ghost Eye" if is_ghost_eye_speak_request else "Space_W"
            self.send_json(
                409,
                {
                    "ok": False,
                    "error": f"{disabled_label} server Whisper is disabled. Use browser live voice check.",
                    "code": disabled_code,
                    "space_w_ai_check_voice_enabled": False,
                },
            )
            return
        expected = clean(fields.get("expected", ""))
        language = clean(fields.get("language", SERVER_STATE.get("language", "en"))) or "en"
        model_name = clean(fields.get("model", SERVER_STATE.get("model_name", "small"))) or "small"
        suffix = Path(clean(audio_item.get("filename", "recording.webm"))).suffix or ".webm"
        audio_dir = Path(tempfile.gettempdir()) / "future_whisper_recordings"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / f"future_{int(time.time())}_{uuid.uuid4().hex}{suffix}"
        with audio_path.open("wb") as fh:
            fh.write(audio_item["data"])
        stt_debug_log(
            "request_audio_saved",
            audio_path=str(audio_path),
            audio_size=audio_path.stat().st_size if audio_path.is_file() else 0,
            upload_filename=clean(audio_item.get("filename", "")),
            upload_content_type=clean(audio_item.get("content_type", "")),
            expected_chars=len(expected),
            language=language,
            model_name=model_name,
        )
        result = submit_worker_transcription(str(audio_path), model_name, language, expected, preferred_user=preferred_user)
        stt_debug_log("request_transcribe_result", audio_path=str(audio_path), job_id=result.get("job_id", ""), text=clean(result.get("text", "")), words=len(result.get("words", []) or []))
        text = clean(result.get("text", ""))
        words = list(result.get("words", []) or [])
        scoring = {key: result.get(key) for key in ("score", "correct", "total", "extra_words", "missing_words", "details", "feedback", "speech_training") if key in result} if expected else {}
        self.send_json(
            200,
            {
                "ok": True,
                "text": text,
                "words": words,
                "audio_path": str(audio_path),
                "job_id": result.get("job_id", ""),
                "queue_position": result.get("queue_position", 0),
                "queue_wait_ms": result.get("queue_wait_ms", 0),
                "queue_process_ms": result.get("queue_process_ms", 0),
                "model": SERVER_STATE.get("model_name", model_name),
                "model_ref": SERVER_STATE.get("model_ref", ""),
                "language": language,
                **scoring,
            },
        )
    except Exception as exc:
        SERVER_STATE.update({"loading": False, "last_error": str(exc)})
        stt_debug_log("request_exception", error=str(exc), traceback=traceback.format_exc())
        self.send_json(500, {"ok": False, "error": str(exc)})
